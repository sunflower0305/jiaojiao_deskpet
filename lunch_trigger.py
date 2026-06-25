#!/usr/bin/env python3
"""
午饭触发器 — 在 11:45-13:00 之间向 clawd-on-desk 推送 eating 状态。
用法：
  直接运行：python lunch_trigger.py
  Windows 任务计划程序：每天 11:45 触发一次即可，脚本内部等待窗口结束后自动退出。
"""

import json
import random
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

RUNTIME_JSON = Path.home() / ".clawd" / "runtime.json"
DEFAULT_PORT = 23333
EATING_DURATION_SEC = 60   # eating 状态持续时间（秒），之后恢复 idle
WINDOW_START = (11, 45)    # 触发窗口开始
WINDOW_END   = (13,  0)    # 触发窗口结束

EATING_PHRASES = [
    "好好吃！",
    "嗷呜~",
    "吃饭时间！",
    "咔嚓咔嚓~",
    "好香呀~",
    "今天也要好好吃饭！",
    "最喜欢吃饭了！",
]


def get_port():
    try:
        data = json.loads(RUNTIME_JSON.read_text())
        return int(data.get("port", DEFAULT_PORT))
    except Exception:
        return DEFAULT_PORT


def post_state(port, state, session_id="default"):
    payload = json.dumps({"state": state, "session_id": session_id}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/state",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except urllib.error.URLError:
        return False


def post_speech(port, text, duration_ms=4000):
    payload = json.dumps({"text": text, "durationMs": duration_ms}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/speech",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status == 200
    except urllib.error.URLError:
        return False


def in_window():
    now = datetime.now()
    t = (now.hour, now.minute)
    return WINDOW_START <= t < WINDOW_END


def main():
    # 如果不在时间窗口内，直接退出（任务计划程序可能提前触发）
    if not in_window():
        print(f"[lunch_trigger] 当前不在触发窗口 {WINDOW_START}-{WINDOW_END}，退出。")
        return

    port = get_port()
    print(f"[lunch_trigger] 推送 eating 状态到端口 {port}")
    ok = post_state(port, "eating")
    if ok:
        phrase = random.choice(EATING_PHRASES)
        post_speech(port, phrase, duration_ms=5000)
        print(f"[lunch_trigger] eating 状态已触发（{phrase!r}），持续 {EATING_DURATION_SEC} 秒后恢复。")
        time.sleep(EATING_DURATION_SEC)
        post_state(port, "idle")
        print("[lunch_trigger] 已恢复 idle。")
    else:
        print("[lunch_trigger] 推送失败，clawd-on-desk 可能未运行。")


if __name__ == "__main__":
    main()
