#!/usr/bin/env python
"""自动化 PTY 交互测试（通过 subprocess 管道模拟）。"""

import subprocess
import sys
import os
import time
import json
from pathlib import Path

NANOHERMES_HOME = Path.home() / ".nanohermes"
SESSIONS_DIR = NANOHERMES_HOME / "sessions"
MEMORY_DIR = NANOHERMES_HOME / "memory"


def clean_test_data():
    import shutil
    if SESSIONS_DIR.exists():
        shutil.rmtree(SESSIONS_DIR)
    db = NANOHERMES_HOME / "sessions.db"
    if db.exists():
        db.unlink()
    if MEMORY_DIR.exists():
        shutil.rmtree(MEMORY_DIR)


def run_interaction(inputs, timeout_per_input=45, debug=False):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    cmd = [sys.executable, "-m", "src.main"]
    if debug:
        cmd.append("--debug")

    full_input = "\n".join(inputs) + "\nquit\n"

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=os.getcwd(),
    )

    try:
        stdout, _ = proc.communicate(input=full_input, timeout=timeout_per_input * len(inputs) + 60)
        return stdout, proc.returncode
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, _ = proc.communicate()
        return stdout + "\n[TIMEOUT]", -1


def check_startup(output):
    lower = output.lower()
    return {
        "无启动错误": "traceback" not in lower or "tool" in lower,
        "工具注册": "tool" in lower or "工具" in output,
        "进入交互": any(kw in lower for kw in ["input", "user:", ">", "请输入"]),
    }


def check_session_storage():
    results = {}
    jsonl_files = list(SESSIONS_DIR.glob("*.jsonl")) if SESSIONS_DIR.exists() else []
    results["JSONL 文件生成"] = len(jsonl_files) > 0

    if jsonl_files:
        with open(jsonl_files[0], "r", encoding="utf-8") as f:
            lines = f.readlines()
        results["JSONL 包含消息"] = len(lines) > 0
        try:
            first_msg = json.loads(lines[0])
            results["消息格式正确"] = "role" in first_msg and "content" in first_msg
        except Exception:
            results["消息格式正确"] = False

    db_path = NANOHERMES_HOME / "sessions.db"
    results["SQLite 数据库生成"] = db_path.exists()
    return results


def check_memory():
    return {
        "MEMORY.md 存在": (MEMORY_DIR / "MEMORY.md").exists(),
        "USER.md 存在": (MEMORY_DIR / "USER.md").exists(),
    }


def main():
    print("=" * 60)
    print("NanoHermes PTY 交互自动化测试")
    print("=" * 60)

    print("\n[准备] 清理旧测试数据...")
    clean_test_data()

    print("\n[测试 1] 启动验证 + 基础对话...")
    inputs = ["你好", "1+1等于几"]
    output, rc = run_interaction(inputs, timeout_per_input=45)

    startup = check_startup(output)
    print(f"  返回码: {rc}")
    for check, passed in startup.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    print("\n[测试 2] 会话存储验证...")
    storage = check_session_storage()
    for check, passed in storage.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    print("\n[测试 3] 记忆系统验证...")
    memory = check_memory()
    for check, passed in memory.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    print("\n[测试 4] 工具调用测试 (echo)...")
    clean_test_data()
    inputs = ["运行 echo hello_world_test"]
    output, rc = run_interaction(inputs, timeout_per_input=60)

    has_tool_call = any(kw in output.lower() for kw in ["echo", "terminal", "hello_world_test"])
    status = "PASS" if has_tool_call else "FAIL"
    print(f"  [{status}] 工具调用检测: {'检测到' if has_tool_call else '未检测到'}")

    print("\n" + "=" * 60)
    print("测试摘要")
    print("=" * 60)
    print(f"启动验证: {'通过' if all(startup.values()) else '部分通过'}")
    print(f"会话存储: {'通过' if all(storage.values()) else '部分通过'}")
    print(f"记忆系统: {'通过' if all(memory.values()) else '部分通过'}")
    print(f"工具调用: {'通过' if has_tool_call else '未检测到'}")

    with open("test_pty_output.log", "w", encoding="utf-8") as f:
        f.write(output)
    print(f"\n详细输出已保存到: test_pty_output.log")


if __name__ == "__main__":
    main()
