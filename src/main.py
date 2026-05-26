"""NanoHermes 主入口。

启动方式:
    python -m src.main              # 交互模式
    python -m src.main --test-api   # 测试 API 连接
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def test_api():
    """测试 API 连接。"""
    load_dotenv()

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

    if not api_key:
        print("[错误] 未设置 DASHSCOPE_API_KEY，请在 .env 文件中配置")
        sys.exit(1)

    from openai import OpenAI

    print(f"[连接] {base_url}")
    print(f"[模型] {model}")
    print("[发送测试请求...]\n")

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是 NanoHermes 测试助手。"},
                {"role": "user", "content": "你好，请用一句话回复测试成功。"},
            ],
            max_tokens=50,
        )
        print("[成功] API 连接正常!")
        print(f"[回复] {response.choices[0].message.content}")
        print(f"[用量] 输入 {response.usage.prompt_tokens} tokens, 输出 {response.usage.completion_tokens} tokens")
    except Exception as e:
        print(f"[失败] {type(e).__name__}: {e}")
        sys.exit(1)


def interactive_mode():
    """交互对话模式。"""
    load_dotenv()

    api_key = os.environ.get("DASHSCOPE_API_KEY")
    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

    if not api_key:
        print("[错误] 未设置 DASHSCOPE_API_KEY，请在 .env 文件中配置")
        sys.exit(1)

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    # 初始化会话
    from src.session.session_db import SessionDB
    db_path = Path.home() / ".nanohermes" / "sessions.db"
    db = SessionDB(db_path)
    session_id = db.create_session(model=model, provider="dashscope")
    print(f"[会话] {session_id}")

    messages = [
        {"role": "system", "content": "你是 NanoHermes，一个有用的 AI 助手。"},
    ]

    print("=" * 50)
    print("  NanoHermes v0.1.0 - 交互对话模式")
    print("  输入 'quit' 或 'exit' 退出")
    print("  输入 'clear' 清空对话")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[退出] 再见!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("[退出] 再见!")
            break

        if user_input.lower() == "clear":
            messages = [messages[0]]  # 保留 system message
            print("[清空] 对话已清空")
            continue

        if not user_input:
            continue

        # 保存用户消息
        db.insert_message(session_id, "user", user_input)
        messages.append({"role": "user", "content": user_input})

        print("\n[思考中]...", end="", flush=True)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=4096,
            )

            content = response.choices[0].message.content or ""
            messages.append({"role": "assistant", "content": content})

            # 保存助手消息
            db.insert_message(session_id, "assistant", content)
            db.update_token_counts(
                session_id,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                incremental=True,
            )

            print(f"\n{content}")

        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}")

    db.close()


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(description="NanoHermes - 自进化 AI Agent 系统")
    parser.add_argument("--test-api", action="store_true", help="测试 API 连接")
    args = parser.parse_args()

    if args.test_api:
        test_api()
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
