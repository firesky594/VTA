import queue
import traceback
from vtaTools.FrameSaver import FrameSaver
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
        self.vision_queue = self.manager.Queue(maxsize=10)
        self.think_queue = self.manager.Queue(maxsize=10)
        self.action_queue = self.manager.Queue(maxsize=10)
        self.processes = {}
        # 2. 【核心配置】指定扫描的文件夹
        self.TOOL_PKGS = ["visionTools", "actionTools", "thinkTools"]
        # 3. 【自动注册】扫描并启动所有 Worker
        self.discover_and_start_workers(tools_pkgs=self.TOOL_PKGS)

    def discover_and_start_workers(self, tools_pkgs=None):
        """ 扫描指定目录，寻找 IS_WORKER 标记的模块并启动 """
        log_info("HQZ", "正在自动扫描 Worker 模块...")
        for pkg in tools_pkgs or self.TOOL_PKGS:
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
        log_info("HQZ", f"关闭旧进程 {name}...")
        """ 进程管理核心：安全杀掉旧的，启动新的 """
        if name in self.processes:
            p_old = self.processes[name]
            if p_old.is_alive():
                p_old.terminate()
                p_old.join(timeout=1)

        log_info("HQZ", f"启动新进程 {name}...")
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
                    self.restart_process(mod_name.lower(), target_func, (self.vision_queue, self.think_queue, self.action_queue, self.shared_data))
                    log_success("HQZ", f"检测到 Worker 变更，进程 {mod_name} 已重启")
            else:
                log_success("HQZ", f"子模块 {full_mod_name} 热重载")
                # ✅ 判断是否在 src 目录
                if os.sep + "src" + os.sep in abs_path:
                    parent_pkg = parts[-3]   # visionTools / actionTools / thinkTools
                    log_info("HQZ", f"检测到 src 变更，准备重启 {parent_pkg} 下所有 Worker")
                    self._restart_related_workers(parent_pkg)

    def _restart_related_workers(self, src_pkg_name):
        log_info("HQZ", f"正在重启与 {src_pkg_name} 相关的 Worker...")
        self.discover_and_start_workers(tools_pkgs=[src_pkg_name])

    def draw_grid(self, frame, step=50, color=(200, 200, 200), show_text=True):
        """
        在图像上绘制网格和坐标
        :param frame: 原始图像
        :param step: 网格间距，默认100像素
        :param color: 线条颜色 (B, G, R)
        :param show_text: 是否显示坐标刻度数字
        :return: 带有网格的副本图像
        """
        if frame is None:
            return None

        # 拷贝一份防止修改原图
        canvas = frame.copy()
        h, w = canvas.shape[:2]

        # 绘制垂直线
        for x in range(0, w, step):
            cv2.line(canvas, (x, 0), (x, h), color, 1)
            if show_text:
                cv2.putText(canvas, str(x), (x + 5, 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        # 绘制水平线
        for y in range(0, h, step):
            cv2.line(canvas, (0, y), (w, y), color, 1)
            if show_text:
                cv2.putText(canvas, str(y), (5, y + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

        return canvas

    def run(self):
        frame_saver = FrameSaver()  # 初始化 FrameSaver，确保目录准备就绪
        log_success("HQZ", "主循环启动：负责接收视觉数据、思考并执行动作整套流程")
        try:
            while self.shared_data["shutdown"] is False:
                if not self.vision_queue.empty():

                    try:
                        frame = self.vision_queue.get(timeout=0.1)  # 队列空会抛 queue.Empty
                    except queue.Empty:
                        pass
                    frame = self.draw_grid(frame)
                    if frame is not None and frame.size > 0:
                        cv2.imshow("HQZ Display", frame)
                        key = cv2.waitKey(1) & 0xFF
                        if key == ord('q'):
                            break
                        elif key == ord('f'):
                            log_info("GA", "用户按下 [F]，触发 手动分割识别")
                            frame_saver.auto_save(frame, reason="手动截图分析")
                    else:
                        log_error("HQZ", "收到无效帧，跳过显示")
                        time.sleep(10)  # 等待一小会儿，避免过度占用 CPU

                time.sleep(0.01)  # 避免 CPU 占用过高
        except Exception as e:
            log_error("HQZ", f"主循环异常: {repr(e)}")
            traceback.print_exc()
            cv2.destroyAllWindows()

    def shutdown(self):
        log_info("HQZ", "开始优雅关闭...")
        # 1️⃣ 通知所有 worker 自己退出
        self.shared_data["shutdown"] = True
        self.manager.shutdown()
        for q in [self.vision_queue, self.think_queue, self.action_queue]:
            try:
                q.close()
                q.join_thread()
            except:
                pass
        # 2️⃣ 等待所有 worker 进程退出
        for name, proc in self.processes.items():
            log_info("HQZ", f"等待 Worker [{name}] 退出...")
            proc.join(timeout=5)
            if proc.is_alive():
                log_error("HQZ", f"Worker [{name}] 未能及时退出，强制终止")
                proc.terminate()
                proc.join(timeout=1)
                log_info("HQZ", f"Worker [{name}] 已强制终止")
        log_info("HQZ", "所有 Worker 已成功关闭")
