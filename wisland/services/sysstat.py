# -*- coding: utf-8 -*-
"""系统资源读数（收起态胶囊用）：CPU、内存占用，以及网络上行 / 下行速率。

信号 updated(dict)：{cpu: %, mem: %, up: B/s, down: B/s}

成本（本机实测）：cpu_percent 0.03ms、virtual_memory 0.026ms —— 主线程直接采；
net_io_counters 约 3.5ms（网卡多时更慢）—— 放后台线程，别卡 UI。

两个坑：
  1. net_io_counters 会把物理网卡和 VPN / TUN 一起累加，开着 Clash TUN 时流量会翻倍，
     所以只统计「在线 + 非虚拟」的网卡；
  2. 休眠唤醒后两次采样间隔很长，字节差除以大间隔虽然不会离谱，但计数器可能已回绕/重置，
     间隔超过 MAX_GAP 直接丢掉这次样本，避免跳出一个巨大的瞬时速率。
"""
from __future__ import annotations

import time

import psutil
from PySide6 import QtCore

from wisland.core.bg import run_bg
from wisland.core.config import cfg

# 虚拟 / 隧道网卡的名字特征（小写包含匹配）：这些流量已计入它们经过的物理网卡
_VIRTUAL = ("vethernet", "virtualbox", "vmware", "hyper-v", "wintun", "tailscale", "zerotier",
            "loopback", "npcap", "tap-", "tap0", "tun", "vpn", "wireguard", "openvpn",
            "docker", "br-", "bluetooth", "teredo", "isatap")
_MAX_GAP = 5.0          # 两次采样间隔超过这个值（休眠 / 卡顿）就丢弃本次速率
_IFACE_TTL = 60.0       # 网卡列表缓存时间


def _has_mac(addrs) -> bool:
    """是否有真实的物理地址（虚拟网卡和回环通常是空的或全 0）。"""
    for a in addrs or ():
        if a.family == psutil.AF_LINK and (a.address or "").strip("0-: "):
            return True
    return False


def fmt_rate(bps: float) -> str:
    """字节/秒 -> 1.2K / 8.4M / 999M（不带 B/s 后缀，省宽度）。

    约定输出最长 4 个字符：胶囊里的槽位宽度是按 4 字符预留的，超了这一格就会挤到下一项。
    所以每档都以 999.5 为界（再取整也不会变成 1024K 这类 5 字符）。
    """
    try:
        v = float(bps or 0)
    except (TypeError, ValueError):
        return "0"
    if v < 1024:
        return str(int(v))                      # 0 ~ 1023，最多 4 个数字
    for unit, base in (("K", 1024.0), ("M", 1024.0 ** 2), ("G", 1024.0 ** 3)):
        n = v / base
        if n < 999.5:
            return f"{n:.1f}{unit}" if n < 10 else f"{n:.0f}{unit}"
    n = v / 1024.0 ** 4                         # 1T/s 以上（现实中不会出现，兜底不超宽）
    return f"{n:.1f}T" if n < 10 else f"{n:.0f}T"


class SysStatService(QtCore.QObject):
    updated = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {"cpu": 0.0, "mem": 0.0, "up": 0.0, "down": 0.0}
        self._last: tuple[float, int, int] | None = None
        self._ifaces: set[str] = set()
        self._ifaces_t = 0.0
        self._busy = False
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ---------- lifecycle ----------
    def start(self):
        try:
            sec = float(cfg.get("compact.interval") or 1.0)
        except (TypeError, ValueError):
            sec = 1.0
        self._timer.start(int(max(0.5, min(10.0, sec)) * 1000))
        psutil.cpu_percent(None)          # 预热：首次调用恒为 0
        self._net_rates()                 # 建立字节计数基线
        # 等一小会儿再出第一帧，否则 cpu_percent 的第一次读数是 0%
        QtCore.QTimer.singleShot(300, self._tick)

    def stop(self):
        self._timer.stop()

    # ---------- 采样 ----------
    def _tick(self):
        if self._busy:                    # 上一轮后台还没回来，跳过（网速慢时不会堆积）
            return
        self._busy = True
        try:
            cpu = psutil.cpu_percent(None)
            mem = psutil.virtual_memory().percent
        except Exception:  # noqa: BLE001
            self._busy = False
            return
        run_bg(self._net_rates, on_done=lambda net: self._apply(cpu, mem, net),
               on_error=lambda e: self._apply(cpu, mem, None))

    def _apply(self, cpu: float, mem: float, net):
        self._busy = False
        d = dict(self.data)
        d["cpu"], d["mem"] = cpu, mem
        if net is not None:
            d["up"], d["down"] = net
        self.data = d
        self.updated.emit(dict(d))

    def _net_rates(self):
        """后台线程：累计字节差分 -> 速率（B/s）。首次只建立基线，返回 None。"""
        now = time.monotonic()
        try:
            recv, sent = self._totals()
        except Exception:  # noqa: BLE001
            return None
        last, self._last = self._last, (now, recv, sent)
        if last is None:
            return None
        dt = now - last[0]
        if dt < 0.2 or dt > _MAX_GAP:
            return None
        return (max(0.0, (sent - last[2]) / dt), max(0.0, (recv - last[1]) / dt))

    def _totals(self) -> tuple[int, int]:
        names = self._pick_ifaces()
        recv = sent = 0
        for name, io in psutil.net_io_counters(pernic=True).items():
            if name in names:
                recv += io.bytes_recv
                sent += io.bytes_sent
        return recv, sent

    def _pick_ifaces(self) -> set[str]:
        """在线、非虚拟、且有物理地址的网卡名（缓存 60 秒）。全被滤掉时退回全部网卡。"""
        now = time.monotonic()
        if self._ifaces and now - self._ifaces_t < _IFACE_TTL:
            return self._ifaces
        names: set[str] = set()
        try:
            addrs = psutil.net_if_addrs()
            for name, st in psutil.net_if_stats().items():
                if not st.isup:
                    continue
                low = name.lower()
                if any(h in low for h in _VIRTUAL):
                    continue
                if not _has_mac(addrs.get(name)):
                    continue          # 虚拟网卡 / 回环没有物理地址（如 vgate0、Loopback）
                names.add(name)
        except Exception:  # noqa: BLE001
            names = set()
        if not names:
            try:
                names = set(psutil.net_io_counters(pernic=True))
            except Exception:  # noqa: BLE001
                names = set()
        self._ifaces, self._ifaces_t = names, now
        return names
