import cv2
import numpy as np
import time
import queue
from share_data import SHARED_DATA_TEMPLATE
import mss
from vtaTools.ColorLog import log_success, log_error, log_info


IS_WORKER = True

MONITOR_ID = 2


def select_roi_from_monitor(monitor_id=1, max_width=1280):
    ix, iy = -1, -1
    drawing = False
    roi = None

    with mss.mss() as sct:
        monitors = sct.monitors

        if monitor_id >= len(monitors):
            raise ValueError("Invalid monitor_id")

        monitor = monitors[monitor_id]
        screenshot = np.array(sct.grab(monitor))
        img = cv2.cvtColor(screenshot, cv2.COLOR_BGRA2BGR)

    h, w = img.shape[:2]

    # ===== 自动缩放（关键）=====
    scale = min(1.0, max_width / w)
    resized = cv2.resize(img, (int(w * scale), int(h * scale)))

    clone = resized.copy()

    def mouse(event, x, y, flags, param):
        nonlocal ix, iy, drawing, roi

        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            ix, iy = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if drawing:
                temp = resized.copy()
                cv2.rectangle(temp, (ix, iy), (x, y), (0, 255, 0), 2)
                cv2.imshow("Select ROI", temp)

        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False

            x1, y1 = min(ix, x), min(iy, y)
            x2, y2 = max(ix, x), max(iy, y)

            # ===== 转换回原始坐标 =====
            roi = [
                int(x1 / scale),
                int(y1 / scale),
                int((x2 - x1) / scale),
                int((y2 - y1) / scale),
            ]

            print("ROI:", roi)

    cv2.namedWindow("Select ROI")
    cv2.setMouseCallback("Select ROI", mouse)

    while True:
        cv2.imshow("Select ROI", resized)
        key = cv2.waitKey(1) & 0xFF

        if key == 13 and roi is not None:  # Enter确认
            break
        elif key == ord("r"):
            resized = clone.copy()
            roi = None
        elif key == ord("q"):
            roi = None
            break

    cv2.destroyAllWindows()
    return roi


def worker_run(vision_queue, think_queue, action_queue, shared):
    log_info("MSSWorker", "mss_worker started")
    """ 将MSS的ROI区域放到vision_queue去 """
    sct = mss.mss()
    # ========= 获取屏幕 =========
    monitors = sct.monitors
    if MONITOR_ID >= len(monitors):
        log_error("MSSWorker", f"Invalid monitor id: {MONITOR_ID}")
        return

    monitor = monitors[MONITOR_ID]

    ROI_LOCATION = select_roi_from_monitor(MONITOR_ID)
    # ========= ROI =========
    x, y, w, h = ROI_LOCATION
    log_info("MSSWorker", f"Selected ROI: {x}, {y}, {w}, {h}")
    if w == 0 or h == 0:
        log_error("MSSWorker", "ROI not set")
        return

    roi_monitor = {
        "top": monitor["top"] + y,
        "left": monitor["left"] + x,
        "width": w,
        "height": h
    }

    log_success("MSSWorker", f"Using ROI: {roi_monitor}")

    # ========= 主循环 =========
    while True:
        try:
            # ====== 截图 ======
            frame = np.array(sct.grab(roi_monitor))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # ====== 队列策略：只保留最新帧 ======
            if vision_queue.full():
                try:
                    vision_queue.get_nowait()
                except queue.Empty:
                    pass

            vision_queue.put_nowait(frame)

        except Exception as e:
            log_error("MSSWorker", str(e))

        # 控制帧率（关键）
        time.sleep(0.2)
