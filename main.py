import multiprocessing as mp
import threading
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from HQZAssistant import HQZAssistant
from vtaTools.ColorLog import log_success, log_error, log_info
import os
import time
import sys
import cv2
import psutil


class ReloadHandler(PatternMatchingEventHandler):
    def __init__(self, callback, procs_to_kill=None):
        super().__init__(
            patterns=["*.py"],
            ignore_patterns=[
                "*/__pycache__/*",
                "*/.git/*",
                "*/models/*",
                "*/datasets/*",
                "*/logs/*",
                "*/.venv/*"
            ],
            ignore_directories=True,
            case_sensitive=False
        )
        self.callback = callback
        self.procs_to_kill = procs_to_kill or []
        self.last_mtime = {}

    def on_any_event(self, event):
        log_info("Main", f"检测到文件更新: {event.src_path}")

    def on_modified(self, event):
        path = os.path.abspath(event.src_path)
        try:
            current_mtime = os.path.getmtime(path)
        except OSError:
            return
        # 去抖动
        if current_mtime == self.last_mtime.get(path):
            return
        self.last_mtime[path] = current_mtime

        fname = os.path.basename(path)
        # 核心文件修改 -> 全量重启
        if fname in ["main.py", "HQZAssistant.py"]:
            log_success("System", f"核心框架 {fname} 修改，全量重启中...")
            # --- 核心清理逻辑 ---
            parent = psutil.Process(os.getpid())
            for child in parent.children(recursive=True):
                child.kill()

            time.sleep(0.5)
            os.execv(sys.executable, [sys.executable] + sys.argv)

        # 调用 HQZAssistant 的模块热重载
        log_success("Main", f"检测到文件更新: {fname}")
        self.callback(path)


if __name__ == "__main__":
    # 循环保护防止初始化失败退出
    mp.freeze_support()
    mp.set_start_method('spawn', force=True)

    assistant = None
    while assistant is None:
        try:
            assistant = HQZAssistant()
            log_success("Main", "HQZAssistant 初始化成功")
        except Exception as e:
            log_error("Main", "HQZAssistant 初始化失败", f"初始化失败: {e}。请修改代码，5秒后重试...")
            time.sleep(5)

    observer = Observer()
    observer.schedule(ReloadHandler(assistant.hot_reload_module), path=".", recursive=True)
    observer.start()

    try:
        assistant.run()
    except Exception as e:
        log_error("Main", f"运行中发生崩溃: {e}")
    finally:
        # 1. 停止监听器 (非常关键，否则主线程关不掉)
        if 'observer' in locals():
            observer.stop()
            observer.join(timeout=1)

        # 2. 强杀训练进程
        try:
            this_process = psutil.Process(os.getpid())
            for child in this_process.children(recursive=True):
                child.kill()
        except:
            pass

        # 3. 执行核心清理
        if assistant:
            try:
                assistant.shutdown()
            except:
                pass

        cv2.destroyAllWindows()
        log_success("Main", "系统已彻底停机")

        # 4. 终极手段：强制退出，不触发任何 Python 析构逻辑
        os._exit(0)
