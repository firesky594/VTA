import os
import subprocess
import time
import queue
from vtaTools.TTSService import TTSService
from vtaTools.ColorLog import log_info, log_error, log_success

# 假设这是你的 TTS 服务类定义
# from your_tts_module import TTSService
ref_audio = "F:/ai_test/OmniVoice/output/omnivoice_1776239735.wav"
IS_WORKER = True

vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"


def worker_run(vision_queue, think_queue, action_queue, shared):
    print("TTS speaker worker started")

    # 1. 初始化 TTS 服务
    # 注意：确保服务在 127.0.0.1:11808 已经启动
    tts = TTSService(host="127.0.0.1", port=11808)

    # 确保临时目录存在
    output_dir = "temp_audio"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    while True:
        # 检查是否有关闭信号
        if shared.get("shutdown") is True:
            break

        if action_queue.empty():
            continue

        try:
            # 2. 从 action_queue 拉取任务 (阻塞模式，超时 0.5 秒)
            task = action_queue.get(timeout=0.5)
            log_info(f"Received task: {task}")
            if task.get("type") == "tts":
                text = task.get("text")
                if not text:
                    continue

                # 生成唯一的文件名，防止并发播放冲突
                filename = f"tts_{int(time.time() * 1000)}.wav"
                output_path = os.path.join(output_dir, filename)

                print(f"Generating TTS: {text}")

                # 3. 调用 TTS 生成音频
                try:
                    tts.text_to_speech(
                        text,
                        ref_audio=ref_audio,
                        output_path=output_path
                    )

                    # 4. 调用 VLC 播放
                    # --play-and-exit: 播放完自动退出进程
                    # -Idummy: 不显示 VLC 图形界面
                    if os.path.exists(output_path):
                        print(f"Playing: {output_path}")
                        # 使用 subprocess.run 会阻塞直到播放完成
                        subprocess.run([
                            vlc_path,
                            "-Idummy",
                            "--play-and-exit",
                            "--no-loop",
                            "--no-repeat",
                            os.path.abspath(output_path)
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        # 5. 播放完删除文件
                        time.sleep(0.1)
                        try:
                            os.remove(output_path)
                        except Exception as e:
                            print(f"Delete Error: {e}")

                except Exception as e:
                    print(f"TTS Process Error: {e}")

            # 标记任务完成
            # action_queue.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            print(f"Worker Loop Error: {e}")

    print("TTS speaker worker stopped")
