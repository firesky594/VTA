import sqlite3
import re
import time
import queue
from vtaTools.ColorLog import log_info, log_error, log_success
IS_WORKER = True


def clean_text(text):
    if not isinstance(text, str):
        return None

    text = text.strip()
    if not text:
        return None

    # 去掉纯符号/垃圾
    if not re.search(r'[\u4e00-\u9fa50-9]', text):
        return None

    return text


def parse_line(text):
    text = clean_text(text)
    if not text:
        return None

    # 1. 增强：匹配进场（包含“来了”或“欢迎”前缀）
    # 匹配：欢迎 智海 或 12智海来了
    m_enter = re.search(r"(?:欢迎\s*)?(.+?)(?:来了)?$", text)
    # 如果文本纯粹是“欢迎 xxx”，我们也视作 enter 状态
    if "欢迎" in text and "：" not in text and ":" not in text:
        name = text.replace("欢迎", "").strip()
        return {"level": None, "name": name, "status": "enter", "content": ""}

    if m_enter and ("来了" in text):
        return {
            "level": None,  # 等级由 merge_lines 的 buffer 处理
            "name": m_enter.group(1).strip(),
            "status": "enter",
            "content": ""
        }

    # 2. 匹配弹幕 “名字：内容”
    if "：" in text or ":" in text:
        parts = re.split(r'：|:', text, maxsplit=1)
        return {
            "level": None,
            "name": parts[0].strip(),
            "status": "speak",
            "content": parts[1].strip()
        }

    # 3. 兜底：纯文本
    return {
        "level": None,
        "name": None,
        "status": "speak",
        "content": text
    }


def merge_lines(lines):
    merged = []
    buffer_level = None
    last_event = None  # 记录上一条处理过的事件对象

    for raw in lines:
        text = clean_text(raw)
        if not text:
            continue

        # 1. 处理等级数字 (例如 '25')
        if text.isdigit() and len(text) <= 2:
            buffer_level = int(text)
            continue

        event = parse_line(text)
        if not event:
            continue

        # 2. 判断是否是接续句子
        # 条件：status为speak，且没有name（兜底产生的），且前面已经有正在说话的人
        if event["status"] == "speak" and event["name"] is None:
            if last_event and last_event["status"] == "speak":
                # 将内容连接到上一句，不产生新事件
                last_event["content"] += " " + event["content"]
                continue
            # 如果前面没人在说话，这一句只能作为独立无名消息处理（保持原样）

        # 3. 关联等级到当前新事件
        if buffer_level:
            event["level"] = buffer_level
            buffer_level = None

        # 4. 更新状态并存入列表
        merged.append(event)
        last_event = event

    return merged


def upsert_event(conn, event, window=10):
    cursor = conn.cursor()
    now = time.time()

    name = event["name"]

    # 1. 去重判断
    if name is None:
        cursor.execute("""
            SELECT 1 FROM messages
            WHERE name IS NULL
            AND status = ?
            AND content = ?
            LIMIT 1
        """, (event["status"], event["content"]))
    else:
        cursor.execute("""
            SELECT 1 FROM messages
            WHERE name = ?
            AND status = ?
            AND content = ?
            LIMIT 1
        """, (name, event["status"], event["content"]))

    if cursor.fetchone():
        return False

    # 2. 插入
    cursor.execute("""
        INSERT INTO messages (level, name, status, content, ts)
        VALUES (?, ?, ?, ?, ?)
    """, (
        event.get("level"),
        name,
        event["status"],
        event["content"],
        now
    ))

    conn.commit()
    return "inserted"


def worker_run(vision_queue, think_queue, action_queue, shared):
    conn = sqlite3.connect("messages.db", check_same_thread=False)
    # === 新增：初始化建表逻辑 ===
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level INTEGER,
            name TEXT,
            status TEXT,
            content TEXT,
            ts REAL
        )
    """)
    conn.commit()
    # log_info("CONN OPEN", conn)
    while True:
        if shared.get("shutdown") is True:
            break
        try:
            data = shared.get("audio_text_list", [])
            if data:
                shared["audio_text_list"] = []  # 拿走就立刻清空，不要 sleep
            else:
                time.sleep(0.5)  # 没数据时才休息
                continue
        except:
            continue
        if not data:
            continue
        # log_info("data:", data)
        merged = merge_lines(data)

        for event in merged:
            # log_info("event:", event)
            result = upsert_event(conn, event)
            # log_info("result:", result)
            if not result:
                continue
            # ==== TTS 优化 ====
            if event["status"] == "enter":
                text = f"欢迎 {event['name']}"  # 稍微口语化一点
            else:
                if event["name"]:
                    text = f"{event['name']}说 {event['content']}"
                else:
                    text = f"{event['content']}"  # 没有名字就直接念内容

            log_info("TTS Wait to say:", text)
            if action_queue.full():
                try:
                    action_queue.get_nowait()
                except queue.Empty:
                    pass
            action_queue.put_nowait({
                "type": "tts",
                "text": text
            })
