# -*- coding: utf-8 -*-
r"""重启支持：「等上一个实例退出」再把自己拉起来。

为什么需要等待者：`QLockFile` 的单实例锁在旧进程存活期间会拒绝新实例（打印「wisland 已在运行」后直接退出），
全局热键和托盘图标也会打架。所以重启不能「先起新的再退旧的」，而是拉一个等待者，等旧进程退出后再启动。

等待者本身就是新实例：`run.pyw --restart-after <旧 pid>` 先轮询旧 pid，消失后清掉参数、照常启动 wisland。

启动哪个解释器（踩过的坑）：uv 创建的 `.venv` 里 `Scripts\python.exe` 和 `Scripts\pythonw.exe` **都是控制台程序**
（PE 头 Subsystem = 3），而 `DETACHED_PROCESS` 只表示「不继承父进程的控制台」，并不阻止 Windows 给控制台程序
新分配一个控制台窗口——实测父进程无控制台时，以 DETACHED_PROCESS 拉起控制台程序，子进程 `GetConsoleWindow()`
仍然返回有效窗口句柄，默认终端是 Windows Terminal 时就是一个新标签页，关掉它程序也跟着退出。
所以重启一律优先用「窗口子系统」的基础解释器 `pythonw.exe`（配合 `__PYVENV_LAUNCHER__` 指回 venv），
实在找不到才退回 `CREATE_NO_WINDOW`（实测 hwnd=0，不会有窗口）。
"""
from __future__ import annotations

import os
import struct
import subprocess
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "run.pyw")
POLL_S = 0.15
TIMEOUT_S = 20.0
# DETACHED_PROCESS | NEW_PROCESS_GROUP：不随父进程退出（GUI 程序用来分离足够）
FLAGS_GUI = 0x00000008 | 0x00000200
# CREATE_NO_WINDOW | NEW_PROCESS_GROUP：控制台程序用它才不会弹出窗口（不能与 DETACHED_PROCESS 叠加）
FLAGS_CONSOLE = 0x08000000 | 0x00000200
_GUI, _CONSOLE = 2, 3


def _subsystem(path: str) -> int:
    """读 PE 可选头的 Subsystem 字段：2 = 窗口程序，3 = 控制台程序；读不到返回 0。"""
    try:
        with open(path, "rb") as f:
            head = f.read(0x400)
        if head[:2] != b"MZ":
            return 0
        pe = struct.unpack_from("<I", head, 0x3C)[0]
        magic = struct.unpack_from("<H", head, pe + 0x18)[0]
        if magic not in (0x10B, 0x20B):          # PE32 / PE32+
            return 0
        off = pe + 0x18 + (0x44 if magic == 0x20B else 0x24)
        return struct.unpack_from("<H", head, off)[0]
    except Exception:  # noqa: BLE001
        return 0


def _candidate_dirs() -> list[str]:
    """可能放着基础解释器的目录：先基础解释器（真正带 pythonw.exe 的地方），再自己所在的目录。"""
    dirs = []
    for p in (getattr(sys, "_base_executable", "") or "", sys.executable,
              os.path.join(sys.base_prefix, "python.exe"), os.path.join(sys.prefix, "python.exe")):
        if p:
            d = os.path.dirname(os.path.abspath(p))
            if d and d not in dirs:
                dirs.append(d)
    return dirs


def windowless_exe() -> tuple[str, int]:
    """挑一个不会弹控制台的解释器：返回 (exe, creationflags)。

    优先基础解释器的 `pythonw.exe`（窗口子系统）；找不到才退回当前解释器 + `CREATE_NO_WINDOW`。
    """
    for d in _candidate_dirs():
        pyw = os.path.join(d, "pythonw.exe")
        if os.path.isfile(pyw) and _subsystem(pyw) == _GUI:
            return pyw, FLAGS_GUI
    return sys.executable, FLAGS_CONSOLE


def child_env(exe: str, extra: dict | None = None) -> dict:
    """给新进程准备环境变量。

    - 用基础解释器的 pythonw.exe 启动时，靠 `__PYVENV_LAUNCHER__` 让它认 venv（sys.executable / site-packages）。
    - 顺手去掉 `WISLAND_RELAUNCHED`：那是「已经换过一次解释器」的保险，不能让重启一代代继承下去，
      否则以后每代都跳过「发现自己在控制台里就换 pythonw」的自愈逻辑。
    """
    env = dict(os.environ)
    env.pop("WISLAND_RELAUNCHED", None)
    if os.path.basename(exe).lower() == "pythonw.exe" and sys.prefix != sys.base_prefix:
        venv_py = os.path.join(sys.prefix, "Scripts", "python.exe")
        if os.path.isfile(venv_py):
            env["__PYVENV_LAUNCHER__"] = venv_py
    if extra:
        env.update(extra)
    return env


def pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        import psutil
        return bool(psutil.pid_exists(int(pid)))
    except Exception:  # noqa: BLE001
        return False


def wait_previous(pid: int, timeout: float = TIMEOUT_S) -> bool:
    """等 pid 退出。返回 True = 已退出；False = 超时（调用方照常启动，锁通常也已释放）。"""
    end = time.monotonic() + max(0.0, float(timeout))
    while time.monotonic() < end:
        if not pid_alive(pid):
            return True
        time.sleep(POLL_S)
    return not pid_alive(pid)


def spawn_restart(pid: int | None = None) -> bool:
    """拉起等待者（也就是重启后的新实例）。返回是否成功；失败时调用方不要退出程序。"""
    pid = os.getpid() if pid is None else int(pid)
    if not os.path.isfile(SCRIPT):
        return False
    exe, flags = windowless_exe()
    if not exe:
        return False
    try:
        subprocess.Popen([exe, SCRIPT, "--restart-after", str(pid)], cwd=ROOT,
                         env=child_env(exe), creationflags=flags, close_fds=True)
        return True
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return False
