import cv2
import numpy as np
import time
import queue
import mediapipe as mp

IS_WORKER = True

CAM_ID = 1
TARGET_RATIO = 9 / 16


def worker_run(vision_queue, think_queue, action_queue, shared):
    print("cap_stream_worker started")

    cap = cv2.VideoCapture(CAM_ID)
    if not cap.isOpened():
        print("摄像头打开失败")
        return

    mp_selfie = mp.solutions.selfie_segmentation
    segment = mp_selfie.SelfieSegmentation(model_selection=1)

    ret, frame = cap.read()
    if not ret:
        print("读取失败")
        cap.release()
        return

    h, w = frame.shape[:2]

    roi_w = int(h * TARGET_RATIO)
    roi_h = h

    if roi_w > w:
        roi_w = w
        roi_h = int(w / TARGET_RATIO)

    x = (w - roi_w) // 2
    y = (h - roi_h) // 2

    print(f"ROI: x={x}, y={y}, w={roi_w}, h={roi_h}")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # ========== ROI ==========
        roi = frame[y:y + roi_h, x:x + roi_w]

        # ========== MediaPipe 分割 ==========
        rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        result = segment.process(rgb)

        mask = result.segmentation_mask

        # 二值化（可调阈值）
        condition = mask > 0.5

        # ========== 生成 RGBA ==========
        rgba = np.zeros((roi.shape[0], roi.shape[1], 4), dtype=np.uint8)

        rgba[..., 0:3] = roi
        rgba[..., 3] = condition.astype(np.uint8) * 255

        # ========== 队列处理（只保留最新帧） ==========
        if vision_queue.full():
            try:
                vision_queue.get_nowait()
            except queue.Empty:
                pass

        try:
            vision_queue.put_nowait(rgba)
        except queue.Full:
            pass

        time.sleep(0.01)

    cap.release()
    cv2.destroyAllWindows()
