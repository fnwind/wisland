# -*- coding: utf-8 -*-
"""双击运行（无控制台）：用 .venv\\Scripts\\pythonw.exe run.pyw"""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _relaunch_windowless():
    """uv 创建的 .venv 里 Scripts\\pythonw.exe 其实是控制台程序，直接用它启动（例如旧的开机自启项、
    电脑管家恢复的启动项）会弹出终端窗口，关掉窗口灵动岛也会退出。
    检测到自己挂在控制台上时，改用基础解释器的 pythonw.exe 重新启动自己并立即退出。

    注意：`WISLAND_RELAUNCHED` 只用来防止「换过一次还是带控制台」时无限重生，
    启动后立刻从环境里删掉，否则重启链会一代代继承它，后面的重启就都不再自愈了。
    """
    if os.environ.pop("WISLAND_RELAUNCHED", ""):
        return
    if os.environ.get("WISLAND_CONSOLE"):
        return
    try:
        import ctypes
        if not ctypes.windll.kernel32.GetConsoleWindow():
            return
        import subprocess
        from wisland.relaunch import child_env, windowless_exe
        pyw, flags = windowless_exe()
        if os.path.basename(pyw).lower() != "pythonw.exe":
            return          # 没有窗口子系统解释器可用：保持现状（留着控制台方便看报错），别做无意义的重启
        env = child_env(pyw, {"WISLAND_RELAUNCHED": "1"})
        subprocess.Popen([pyw, os.path.abspath(__file__)] + sys.argv[1:], cwd=ROOT, env=env,
                         creationflags=flags, close_fds=True)
    except Exception:
        return
    os._exit(0)


_relaunch_windowless()


def _wait_previous_instance():
    """由「重启」菜单拉起时带 --restart-after <pid>：先等上一个实例退出（它要保存配置、释放锁），
    再照常启动。等待者自身就是重启后的实例，所以这里只是「晚一点开始」。"""
    args = sys.argv[1:]
    if len(args) != 2 or args[0] != "--restart-after":
        return
    try:
        pid = int(args[1])
    except ValueError:
        return
    sys.argv = [sys.argv[0]]          # 别把内部参数带进后面的启动流程
    try:
        from wisland.relaunch import wait_previous
        wait_previous(pid)
    except Exception:
        import time
        time.sleep(1.5)               # 极端情况（包没就绪）退化成固定等待


_wait_previous_instance()

class _Tee:
    """日志始终写入 data/wisland.log；有控制台时同时输出到控制台。"""
    def __init__(self, *streams):
        self.streams = [x for x in streams if x is not None]

    def write(self, s):
        for x in self.streams:
            try:
                x.write(s)
            except Exception:
                pass

    def flush(self):
        for x in self.streams:
            try:
                x.flush()
            except Exception:
                pass


os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
_log = open(os.path.join(ROOT, "data", "wisland.log"), "a", encoding="utf-8", buffering=1)
sys.stdout = _Tee(sys.stdout, _log)
sys.stderr = _Tee(sys.stderr, _log)

try:
    from wisland.app import main
    sys.exit(main())
except SystemExit:
    raise
except ImportError as e:
    traceback.print_exc()
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        None, f"缺少依赖：{e}\n\n当前 Python：{sys.executable}\n\n请双击项目文件夹里的 setup.bat，"
              "它会把依赖安装进 .venv；装完后再双击 wisland.vbs 启动。", "wisland 启动失败", 0x10)
    sys.exit(1)
except Exception:
    traceback.print_exc()
    raise
