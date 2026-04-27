### 整个流程框架
屏幕捕获 mss
   ↓
ROI裁剪（弹幕区域）
   ↓
OCR（PaddleOCR-VL）
   ↓
文本后处理（去重 + 清洗）
   ↓
Action队列（优先级）queue
   ↓
TTS（OmniVoice）
   ↓
音频播放 播放完之后关闭
### 关键点
1. OCR 去重 + 清洗
2. Action队列（优先级）
3. OCR 服务的安装
4. TTS 服务的安装
5. 数据库的安装(sqlite3)  简单,需要MYSQL的一些基础知识

### 开发过程中的问题
## 1、确定三个队列
    vision_queue：用于存储捕获的frame
    think_queue：用于存储ocr识别到的文本 => shared['ocr_frame']
    action_queue：用于存储tts合成的音频文件名

## 2、确定流程
1. 如何用mss去捕获特定显示屏
2. 如何确定弹幕区域
3. 把捕获的frame放到vision_queue中
4. ocr去从vision_queue中取frame，进行ocr识别+去重+清洗
5. 把需要读出来的文本放到think_queue中
6. OmniVoice去从think_queue中取文本，进行tts保存到文件夹，然后对应的文件名放到action_queue中
7. 播放action_queue中的音频文件
8. 播放完之后关闭音频文件并删除文件

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
## 2. 运行OCR Service 服务
http://127.0.0.1:11880/predict
## 3. 运行TTS Service 服务
http://127.0.0.1:11881/
## 4. OCR 去重 + 清洗
数据模型设计
level 等级
name 名称
status 状态  enter / speak
content 内容  enter时为空
{
    "level": 25,
    "name": "智海",
    "status": "enter",   # enter / speak
    "content": "你好大家"  # enter时为空
}
## 5. 安装数据库
pip install sqlite3

## 6. 调整查重逻辑

