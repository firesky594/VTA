import cv2
import time
import multiprocessing as mp
import importlib
import os
import sys
import psutil
from vtaTools.ColorLog import log_success, log_error, log_info
from share_data import SHARED_DATA_TEMPLATE
BASE_DIR = os.path.abspath(os.path.dirname(__file__) or '.')


def load_module_from_path(mod_name, file_path):
    """通用模块加载器"""
    try:
        spec = importlib.util.spec_from_file_location(mod_name, file_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules[mod_name] = mod
        return mod
    except Exception as e:
        log_error("Loader", f"无法加载 {file_path}: {e}")
        return None


class HQZAssistant:
    def __init__(self):
        # 1. 跨进程基础设施
        self.manager = mp.Manager()
        self.shared_data = self.manager.dict()
        self.shared_data.update(SHARED_DATA_TEMPLATE)
        self.vision_queue = mp.Queue(maxsize=1)
        self.think_queue = mp.Queue(maxsize=1)
        self.action_queue = mp.Queue(maxsize=1)
        self.processes = {}
        # 2. 【核心配置】指定扫描的文件夹
        self.TOOL_PKGS = ["visionTools", "actionTools", "thinkTools"]
        # 4. 【自动注册】扫描并启动所有 Worker
        self.discover_and_start_workers()

    def discover_and_start_workers(self):
        """ 扫描指定目录，寻找 IS_WORKER 标记的模块并启动 """
        log_info("HQZ", "正在自动扫描 Worker 模块...")
        for pkg in self.TOOL_PKGS:
            pkg_path = os.path.join(BASE_DIR, pkg)
            if not os.path.exists(pkg_path):
                continue

            for file in os.listdir(pkg_path):
                if file.endswith(".py") and not file.startswith("__"):
                    file_path = os.path.join(pkg_path, file)
                    mod_name = file.replace(".py", "")
                    full_mod_name = f"{pkg}.{mod_name}"
                    # 动态加载检查
                    mod = load_module_from_path(full_mod_name, file_path)
                    if mod and getattr(mod, "IS_WORKER", False):
                        target_func = getattr(mod, "worker_run", None)
                        if target_func:
                            # 进程名统一用小写文件名
                            self.restart_process(
                                mod_name.lower(), target_func, (self.vision_queue, self.think_queue, self.action_queue, self.shared_data))

    def restart_process(self, name, target_func, args):
        """ 进程管理核心：安全杀掉旧的，启动新的 """
        if name in self.processes:
            p_old = self.processes[name]
            if p_old.is_alive():
                p_old.terminate()
                p_old.join(timeout=1)

        try:
            p = mp.Process(target=target_func, args=args, name=name)
            p.daemon = True
            p.start()
            self.processes[name] = p
            log_success("HQZ", f"Worker 进程 [{name}] 已启动 (PID: {p.pid})")
        except Exception as e:
            log_error("HQZ", f"进程 {name} 启动失败: {e}")

    def hot_reload_module(self, filepath):
        """ 通用热重载：文件一变，自动决定是否重启进程 (逻辑对齐 discover_and_start_workers) """
        # 1. 从路径推导所属包名 (如 visionTools) 和文件名
        abs_path = os.path.abspath(filepath)
        parts = abs_path.split(os.sep)
        pkg = parts[-2]
        mod_name = parts[-1].replace(".py", "")

        # 2. 构造与启动时一致的完整模块名
        full_mod_name = f"{pkg}.{mod_name}"
        # 3. 动态加载模块
        mod = load_module_from_path(full_mod_name, abs_path)
        if mod:
            # 4. 检查是否为 Worker 模块并重启进程
            if getattr(mod, "IS_WORKER", False):
                target_func = getattr(mod, "worker_run", None)
                if target_func:
                    # 进程名使用 mod_name.lower()，与启动逻辑保持一致
                    self.restart_process(
                        mod_name.lower(), target_func, (self.vision_queue, self.think_queue, self.action_queue, self.shared_data))
                    log_success("HQZ", f"检测到 Worker 变更，进程 {mod_name} 已重启")
            else:
                log_success("HQZ", f"模块 {full_mod_name} 热重载成功")

    def run(self):
        log_success("HQZ", "主循环启动：负责接收视觉数据、思考并执行动作整套流程")
        while True:
            try:
                if not self.vision_queue.empty():
                    frame = self.vision_queue.get_nowait()

                    cv2.imshow("HQZ Display", frame)

                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break

                time.sleep(0.01)  # 避免 CPU 占用过高
            except Exception as e:
                log_error("HQZ", f"主循环异常: {e}")

    def shutdown(self):
        """ 强效递归清理并强制退出 """
        log_info("HQZ", "正在全量关闭系统...")

        # 1. 停止采集驱动
        if hasattr(self, "cap"):
            try:
                if hasattr(self.cap, "stop"):
                    self.cap.stop()
            except:
                pass

        # 2. 递归杀死所有子进程 (YoloWorker, SAM2 等)
        try:
            current_process = psutil.Process(os.getpid())
            children = current_process.children(recursive=True)
            for child in children:
                log_info("System", f"正在结束子进程: {child.pid}")
                child.terminate()  # 先温和请求

            # 等待一小会儿让子进程自行清理
            gone, alive = psutil.wait_procs(children, timeout=1)

            # 如果还有没挂的，直接强杀
            for p in alive:
                p.kill()
        except Exception as e:
            print(f"清理进程树时出错: {e}")

        # 3. 释放 OpenCV 窗口
        cv2.destroyAllWindows()

        # 4. 强制终结主进程
        log_success("System", "所有进程已清理，主程序退出。")
        # 使用 os._exit 绕过所有 try/finally 和析构函数，直接杀掉
        os._exit(0)
