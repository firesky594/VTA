import traceback
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(BASE_DIR, ".venv", "Scripts", "python.exe")


class ReloadHandler(PatternMatchingEventHandler):
    def __init__(self, assistant):
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
        self.assistant = assistant
        self.callback = assistant.hot_reload_module
        self.last_mtime = {}

    def on_any_event(self, event):
        log_info("Main", f"{time.strftime('%Y-%m-%d %H:%M:%S')} 文件更新: {event.src_path}")

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
            log_info("Main", "正在通知所有 Worker 停机...")
            self.assistant.shutdown()
            time.sleep(1)
            log_info("Main", "停机成功，正在重启...")
            os.execv(venv_python, [venv_python] + sys.argv)
        else:
            log_success("Main", f"{time.strftime('%Y-%m-%d %H:%M:%S')} 文件更新: {fname}")
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
    observer.schedule(ReloadHandler(assistant), path=".", recursive=True)
    observer.start()

    try:
        assistant.run()
    except Exception as e:
        log_error("Main", f"运行中发生崩溃: {repr(e)}")
        traceback.print_exc()
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
                assistant.manager.shutdown()
                for q in [assistant.vision_queue, assistant.think_queue, assistant.action_queue]:
                    try:
                        q.close()
                        q.join_thread()
                    except:
                        pass
            except:
                pass

        cv2.destroyAllWindows()
        log_success("Main", "系统已彻底停机")
        traceback.print_exc()
        time.sleep(1)  # 确保日志输出完成
        # 4. 终极手段：强制退出，不触发任何 Python 析构逻辑
        os.execv(venv_python, [venv_python] + sys.argv)
