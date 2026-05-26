"""NanoHermes 主入口。

启动方式:
    python -m src.main              # 交互模式
    python -m src.main --test-api   # 测试 API 连接

本入口将各核心模块耦合到一起:
- Provider Runtime: 凭证解析 + 客户端构建
- Tool Runtime: 工具注册 + 分发
- Session Storage: 会话持久化
- Conversation Loop: 核心对话循环
- Prompt Assembly: 系统提示组装
- Memory System: 记忆注入
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def test_api():
    """测试 API 连接。"""
    load_dotenv()

    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

    if not api_key:
        print("[错误] 未设置 API Key，请在 .env 文件中配置 DASHSCOPE_API_KEY 或 OPENAI_API_KEY")
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


def build_model_caller(client, model: str):
    """构建模型调用函数，适配 ConversationLoop 接口。

    Args:
        client: OpenAI SDK 客户端实例。
        model: 模型名称。

    Returns:
        调用函数: (messages, tools) -> dict
    """
    def call_model(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = client.chat.completions.create(**kwargs)

        choice = response.choices[0] if response.choices else None
        if not choice:
            return {"content": None, "tool_calls": None}

        message = choice.message
        content = message.content
        tool_calls = None

        if message.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]

        return {
            "content": content,
            "tool_calls": tool_calls,
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        }

    return call_model


def build_tool_dispatcher():
    """构建工具分发函数，适配 ConversationLoop 接口。

    Returns:
        分发函数: (name, args) -> str
    """
    from src.tools.dispatcher import dispatch

    def tool_dispatch(name: str, args: dict[str, Any]) -> str:
        return dispatch(name, args)

    return tool_dispatch


def interactive_mode(debug: bool = False):
    """交互对话模式 - 耦合所有核心模块。

    Args:
        debug: 是否开启 debug 模式。
    """
    load_dotenv()

    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

    if not api_key:
        print("[错误] 未设置 API Key，请在 .env 文件中配置")
        sys.exit(1)

    # ========================================================================
    # 1. 初始化 Provider Runtime - 构建 LLM 客户端
    # ========================================================================
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    model_caller = build_model_caller(client, model)

    # ========================================================================
    # 2. 初始化 Tool Runtime - 工具注册和分发
    # ========================================================================
    from src.tools.registry import discover_tools
    from src.tools.dispatcher import dispatch as tool_dispatch_func

    # 自动发现并注册工具模块
    tools_dir = str(Path(__file__).parent / "tools")
    discover_tools(tools_dir)
    print(f"[工具] 已注册工具: {[t.name for t in __import__('src.tools.registry', fromlist=['ToolRegistry']).ToolRegistry.get_all_tools()]}")

    # ========================================================================
    # 3. 初始化 Session Storage - 会话持久化
    # ========================================================================
    from src.session.session_db import SessionDB
    db_path = Path.home() / ".nanohermes" / "sessions.db"
    db = SessionDB(db_path)
    session_id = db.create_session(model=model, provider="dashscope")
    print(f"[会话] {session_id}")

    # ========================================================================
    # 4. 初始化 Prompt Assembly - 系统提示组装
    # ========================================================================
    from src.prompt.assembler import PromptAssembler
    assembler = PromptAssembler()
    assembler.set_stable([
        "你是 NanoHermes，一个有用的 AI 助手。",
        "你可以使用终端工具执行命令。",
    ])

    # ========================================================================
    # 5. 初始化 Memory System - 记忆注入
    # ========================================================================
    from src.memory.managers import MemoryManager
    from src.memory.file_provider import FileMemoryProvider

    memory_manager = MemoryManager()
    memory_dir = Path.home() / ".nanohermes" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    file_provider = FileMemoryProvider(memory_dir)
    memory_manager.add_provider(file_provider)
    memory_manager.initialize_all({})

    # 预取记忆并注入到 stable 层
    memory_context = memory_manager.build_system_prompt_section()
    if memory_context:
        assembler.set_stable([
            "你是 NanoHermes，一个有用的 AI 助手。",
            "你可以使用终端工具执行命令。",
            memory_context,
        ])

    # ========================================================================
    # 6. 初始化 Conversation Loop - 核心对话循环
    # ========================================================================
    from src.conversation.loop import ConversationLoop
    from src.conversation.error_classifier import ErrorCategory

    loop = ConversationLoop(
        max_iterations=90,
        model_call=model_caller,
        tool_dispatch=tool_dispatch_func,
        debug=debug,
    )

    # 获取工具 schema
    from src.tools.registry import get_tool_schemas
    tool_schemas = get_tool_schemas()

    # ========================================================================
    # 7. 启动交互
    # ========================================================================
    system_prompt = assembler.assemble()
    messages = [{"role": "system", "content": system_prompt}]

    print("=" * 50)
    print("  NanoHermes v0.1.0 - 交互对话模式")
    print("  输入 'quit' 或 'exit' 退出")
    print("  输入 'clear' 清空对话")
    print("  输入 'status' 查看会话状态")
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

        if user_input.lower() == "status":
            session_info = db.get_session(session_id)
            if session_info:
                print(f"[状态] 会话: {session_id}")
                print(f"       模型: {session_info.get('model', 'N/A')}")
                print(f"       输入 Token: {session_info.get('input_tokens', 0)}")
                print(f"       输出 Token: {session_info.get('output_tokens', 0)}")
            continue

        if not user_input:
            continue

        # 保存用户消息
        db.insert_message(session_id, "user", user_input)
        messages.append({"role": "user", "content": user_input})

        print("\n[思考中]...", end="", flush=True)

        try:
            # 运行对话循环（包含工具调用链）
            result = loop.run(messages, tool_schemas if tool_schemas else None)

            content = result.get("final_response", "")
            iterations = result.get("iterations", 0)
            usage = result.get("usage")

            # 保存助手消息
            db.insert_message(session_id, "assistant", content)

            if usage:
                db.update_token_counts(
                    session_id,
                    input_tokens=usage.get("input_tokens", 0),
                    output_tokens=usage.get("output_tokens", 0),
                    incremental=True,
                )

            # 同步记忆
            memory_manager.sync_all(messages)

            print(f"\n{content}")
            if iterations > 1:
                print(f"\n[迭代] {iterations} 轮（含工具调用）")

        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}")

    # 结束会话
    db.end_session(session_id, end_reason="user_quit")
    memory_manager.shutdown_all()
    db.close()


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(description="NanoHermes - 自进化 AI Agent 系统")
    parser.add_argument("--test-api", action="store_true", help="测试 API 连接")
    parser.add_argument("--debug", action="store_true", help="开启 debug 模式，输出请求/响应详情")
    args = parser.parse_args()

    if args.test_api:
        test_api()
    else:
        interactive_mode(debug=args.debug)


if __name__ == "__main__":
    main()
