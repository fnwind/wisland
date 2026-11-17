# -*- coding: utf-8 -*-
"""重启支持：「等上一个实例退出」再把自己拉起来。

为什么需要等待者：`QLockFile` 的单实例锁在旧进程存活期间会拒绝新实例（打印「wisland 已在运行」后直接退出），
全局热键和托盘图标也会打架。所以重启不能「先起新的再退旧的」，而是拉一个等待者，等旧进程退出后再启动。

等待者本身就是新实例：`run.pyw --restart-after <旧 pid>` 先轮询旧 pid，消失后清掉参数、照常启动 wisland。
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "run.pyw")
POLL_S = 0.15
TIMEOUT_S = 20.0
# DETACHED_PROCESS | NEW_PROCESS_GROUP：不弹控制台，也不随父进程退出。
# （CREATE_NO_WINDOW 与 DETACHED_PROCESS 在 Win32 文档里互斥，别叠加）
FLAGS = 0x00000008 | 0x00000200


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
    exe = sys.executable
    if not exe or not os.path.isfile(SCRIPT):
        return False
    try:
        subprocess.Popen([exe, SCRIPT, "--restart-after", str(pid)], cwd=ROOT,
                         creationflags=FLAGS, close_fds=True)
        return True
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return False
