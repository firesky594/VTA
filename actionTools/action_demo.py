import cv2
import numpy as np
import time
import queue

IS_WORKER = True

def worker_run(vision_queue, think_queue, action_queue, shared):
    print("action demo worker started")

