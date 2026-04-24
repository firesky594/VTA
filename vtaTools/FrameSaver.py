import os
import cv2
import time
from datetime import datetime
from vtaTools.ColorLog import log_info, log_success


class FrameSaver:
    def __init__(self, base_path='/tmp/frames'):
        self.base_path = base_path
        self.max_daily_frames = 100
        self.last_save_time = 0
        self.save_interval = 2.0  # 强制保存间隔，防止瞬间存爆硬盘
        today = datetime.now().strftime("%Y-%m-%d")
        self.save_dir = os.path.join(self.base_path, today)
        os.makedirs(self.save_dir, exist_ok=True)
        self.current_count = len([f for f in os.listdir(self.save_dir) if f.endswith('.png')])

    def auto_save(self, frame, reason="manual"):
        # 频率检查
        if time.time() - self.last_save_time < self.save_interval:
            return False

        # 统计当天已保存数量
        self.current_count += 1
        if self.current_count >= self.max_daily_frames:
            return False

        filename = f"{datetime.now().strftime('%H%M%S_%f')}.png"
        save_path = os.path.join(self.save_dir, filename)
        cv2.imwrite(save_path, frame)

        self.last_save_time = time.time()
        log_info("FrameSaver", f"[{reason}] 已存帧 {self.current_count}/100 -> {filename}")
        return True
