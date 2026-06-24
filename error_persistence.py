#!/usr/bin/env python3
"""
报错情绪积累 — Claude Code hook 脚本。

配置方式见 setup_tasks.ps1，或手动把 PostToolUseFailure / Stop 加入
~/.claude/settings.json 的 hooks 字段。

调用方式（Claude Code hook 会把事件 JSON 传给 stdin）：
  python error_persistence.py --event PostToolUseFailure
  python error_persistence.py --event PostToolUse
  python error_persistence.py --event Stop
  python error_persistence.py --persist   # 内部子进程模式，不要手动调用
"""

import json
import sys
import time
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

RUNTIME_JSON    = Path.home() / ".clawd" / "runtime.json"
COUNTER_FILE    = Path.home() / ".clawd" / "error_streak.json"
DEFAULT_PORT    = 23333
ERROR_THRESHOLD = 3      # 连续报错几次触发持久模式
PERSIST_SEC     = 15     # 触发后额外维持 error 状态的秒数


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def get_port():
    try:
        return int(json.loads(RUNTIME_JSON.read_text()).get("port", DEFAULT_PORT))
    except Exception:
        return DEFAULT_PORT


def post_state(port, state):
    payload = json.dumps({"state": state, "session_id": "default"}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/state",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status == 200
    except urllib.error.URLError:
        return False


def read_streak():
    try:
        return int(json.loads(COUNTER_FILE.read_text()).get("streak", 0))
    except Exception:
        return 0


def write_streak(n):
    COUNTER_FILE.parent.mkdir(parents=True, exist_ok=True)
    COUNTER_FILE.write_text(json.dumps({"streak": max(0, n)}))


def spawn_persist_bg(port):
    """在后台进程里维持 error 状态，主进程立即返回。"""
    subprocess.Popen(
        [sys.executable, __file__, "--persist", str(port), str(PERSIST_SEC)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        # Windows: 脱离当前进程组，避免随 Claude Code 进程一起被终止
        creationflags=getattr(subprocess, "DETACHED_PROCESS", 0)
                    | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        close_fds=True,
    )


# ── 子进程持久模式 ────────────────────────────────────────────────────────────

def persist_mode(port, seconds):
    """后台运行：每 2s 重发 error 状态，到期后发 idle。"""
    end = time.time() + seconds
    while time.time() < end:
        post_state(port, "error")
        time.sleep(2)
    post_state(port, "idle")


# ── 主 hook 逻辑 ──────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    # 内部子进程调用
    if args and args[0] == "--persist":
        port = int(args[1]) if len(args) > 1 else get_port()
        secs = int(args[2]) if len(args) > 2 else PERSIST_SEC
        persist_mode(port, secs)
        return

    # 读取 Claude Code 传入的 hook payload（stdin JSON）
    event = args[1] if len(args) >= 2 and args[0] == "--event" else ""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # 如果没有显式 --event，从 payload 里读
    if not event:
        event = payload.get("hook_event_name", "")

    port   = get_port()
    streak = read_streak()

    if event == "Stop":
        write_streak(0)
        return

    if event in ("PostToolUseFailure",):
        streak += 1
        write_streak(streak)
        if streak >= ERROR_THRESHOLD:
            spawn_persist_bg(port)
        return

    if event == "PostToolUse":
        is_error = payload.get("tool_response", {}).get("is_error", False)
        if not is_error and streak > 0:
            write_streak(0)
        return


if __name__ == "__main__":
    main()
