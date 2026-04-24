### 整个流程框架
屏幕捕获 mss
   ↓
ROI裁剪（弹幕区域）
   ↓
OCR（PaddleOCR-VL）
   ↓
文本后处理（去重 + 清洗）
   ↓
消息队列（优先级）queue
   ↓
TTS（OmniVoice）
   ↓
音频播放 播放完之后关闭

### 关键点
1. OCR 去重 + 清洗
2. 消息队列（优先级）

pip install mss

### 开发过程中的问题
## 1、确定三个队列
    ocr_queue：用于存储捕获的frame
    txt_queue：用于存储ocr识别到的文本
    audio_queue：用于存储tts合成的音频文件名
## 2、确定流程
1. 如何用mss去捕获特定显示屏
2. 如何确定弹幕区域
3. 把捕获的frame放到ocr_queue中
4. ocr去从ocr_queue中取frame，进行ocr识别+去重+清洗
5. 把需要读出来的文本放到txt_queue中
6. OmniVoice去从txt_queue中取文本，进行tts保存到文件夹，然后对应的文件名放到audio_queue中
7. 播放audio_queue中的音频文件



### 开发步骤
## 1. 新建文件夹 ai_auto_hdxx_play
git clone https://github.com/firesky594/VTA.git ./
python -m venv .venv
.venv/bin/activate
python --version
pip --version
python -m pip install -U pip

```
    清华源
    pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
    阿里源
    pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
    腾讯源
    pip config set global.index-url http://mirrors.cloud.tencent.com/pypi/simple
    豆瓣源
    pip config set global.index-url http://pypi.douban.com/simple/
    换回默认源
    pip config unset global.index-url
```
pip install -r requirements.txt







