import traceback
import cv2
import numpy as np
import time
import queue
from share_data import SHARED_DATA_TEMPLATE
from vtaTools.ColorLog import log_success, log_error, log_info
from vtaTools.OCRService import OCRService
IS_WORKER = True


def worker_run(vision_queue, think_queue, action_queue, shared):
    log_info("OCRWorker", "ocr_worker started")
    ocr = OCRService()
    last_ocr_time = shared.get("ocr_last_time", 0)
    ocr_interval = shared.get("ocr_interval", 3)
    # ========= 主循环 =========
    while True:
        if shared.get("shutdown") is True:
            break
        ocr_frame = shared.get("ocr_frame")
        if ocr_frame is None:
            continue
        try:
            if time.time() - last_ocr_time < ocr_interval:
                continue
            last_ocr_time = time.time()
            ocr_result = ocr.ocr_with_frame(ocr_frame)
            shared["ocr_last_time"] = last_ocr_time
            if ocr_result.get("status") == "success":
                audio_text_list = [item.get("text", "") for item in ocr_result.get("results", [])]
                # log_info('OCR_TEXT_LIST', audio_text_list)
                shared["audio_text_list"] = audio_text_list

        except Exception as e:
            # 捕获所有异常，防止 worker 崩溃
            log_error("OCRWorker", f"未知异常: {repr(e)}")
            traceback.print_exc()
            time.sleep(1)
        # 控制帧率（关键）
        time.sleep(0.2)
