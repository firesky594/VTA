import requests
import time
import numpy as np
import cv2

class OCRService:
    def __init__(self, api_url="http://127.0.0.1:11880/predict_by_path"):
        self.api_url = api_url
        
    def ocr_with_frame(self, frame):
        """
        将 OpenCV 帧发送到 OCR 服务
        """
        self.api_url = "http://127.0.0.1:11880/predict"
        # 1. 将 numpy 数组(frame) 编码为 jpg 格式
        _, img_encoded = cv2.imencode('.jpg', frame)
        
        # 2. 构造文件对象发送
        files = {'file': ('frame.jpg', img_encoded.tobytes(), 'image/jpeg')}
        
        try:
            response = requests.post(self.api_url, files=files)
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
        
    def ocr_with_path(self, file_path):
        """
        执行基准测试并返回统计结果字典
        """
        payload = {"path": file_path}

        try:
            response = requests.post(self.api_url, json=payload)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"请求失败，状态码: {response.status_code}")

        except Exception as e:
            print(f"请求发生异常: {e}")
        return None


# --- 使用示例 ---
# if __name__ == "__main__":
#     tester = OCRService()
#     # 执行测试
#     results = tester.run(r"F:\ai_test\orc\t3.png")

#     if results:
#         print(results)
