# TTSService.py
import requests
import os

ref_audio = "F:/ai_test/OmniVoice/output/omnivoice_1776239735.wav"


class TTSService:
    """
    调用本地 FastAPI OmniVoice TTS 服务
    """

    def __init__(self, host="127.0.0.1", port=11808):
        self.api_url = f"http://{host}:{port}/tts"
        print(f"[TTSService] Initialized, API URL: {self.api_url}")

    def text_to_speech(
        self,
        text,
        output_path="out.wav",
        instruct=None,
        ref_audio=None,
        ref_text=None,
        speed=1.0,
        num_step=32,
        guidance_scale=2.0,
        language=None
    ):
        """
        生成语音
        """
        files = {}
        data = {
            "text": text,
            "instruct": instruct or "",
            "speed": speed,
            "num_step": num_step,
            "guidance_scale": guidance_scale,
            "ref_text": ref_text or "",
            "language": language or "",
        }

        # 上传参考音频文件
        if ref_audio:
            if not os.path.isfile(ref_audio):
                raise FileNotFoundError(f"ref_audio file not found: {ref_audio}")
            files["ref_audio"] = open(ref_audio, "rb")

        # POST 请求
        response = requests.post(self.api_url, data=data, files=files)
        if files.get("ref_audio"):
            files["ref_audio"].close()

        response.raise_for_status()

        # 写入 WAV 文件
        with open(output_path, "wb") as f:
            f.write(response.content)

        print(f"[TTSService] Saved audio to {output_path}")
        return output_path


# # 测试示例
# if __name__ == "__main__":
#     tts = TTSService(host="127.0.0.1", port=11808)

#     # Voice cloning
#     tts.text_to_speech(
#         "Hello, this is a voice cloning test.",
#         ref_audio=ref_audio,
#         output_path="clone.wav"
#     )
