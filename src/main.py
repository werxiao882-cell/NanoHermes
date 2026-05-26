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
        返回包含 content, tool_calls, usage, reasoning, raw_response, request_body
    """
    def call_model(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if tools:
            # OpenAI API 要求 tools 格式为 [{"type": "function", "function": {...}}]
            kwargs["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]

        response = client.chat.completions.create(**kwargs)

        choice = response.choices[0] if response.choices else None
        if not choice:
            return {"content": None, "tool_calls": None, "reasoning": None, "raw_response": None, "request_body": kwargs}

        message = choice.message
        content = message.content
        tool_calls = None
        reasoning = None

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

        # 提取 reasoning 内容（Qwen 等模型的思考过程）
        if hasattr(message, 'reasoning') and message.reasoning:
            reasoning = message.reasoning
        elif hasattr(message, 'reasoning_content') and message.reasoning_content:
            reasoning = message.reasoning_content

        return {
            "content": content,
            "tool_calls": tool_calls,
            "reasoning": reasoning,
            "usage": {
                "input_tokens": response.usage.prompt_tokens if response.usage else 0,
                "output_tokens": response.usage.completion_tokens if response.usage else 0,
            },
            "raw_response": response.model_dump() if hasattr(response, 'model_dump') else str(response),
            "request_body": kwargs,
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


def interactive_mode(debug: bool = False, resume: str | None = None, resume_title: str | None = None):
    """交互对话模式 - 耦合所有核心模块。

    Args:
        debug: 是否开启 debug 模式。
        resume: 恢复会话 ID，"latest" 表示最近会话。
        resume_title: 通过标题恢复会话。
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
    from src.tools import terminal  # noqa: F401 - 触发终端工具自动注册
    from src.tools import file_tools  # noqa: F401 - 触发文件工具自动注册
    from src.tools.dispatcher import dispatch as tool_dispatch_func

    # 自动发现并注册工具模块
    tools_dir = str(Path(__file__).parent / "tools")
    discover_tools(tools_dir)
    print(f"[工具] 已注册工具: {[t.name for t in __import__('src.tools.registry', fromlist=['ToolRegistry']).ToolRegistry.get_all_tools()]}")

    # ========================================================================
    # 3. 初始化 Session Storage - 会话持久化 + JSONL 历史
    # ========================================================================
    from src.session.session_db import SessionDB
    from src.session.jsonl_store import JsonlSessionStore

    db_path = Path.home() / ".nanohermes" / "sessions.db"
    db = SessionDB(db_path)
    jsonl_store = JsonlSessionStore()

    # 会话恢复逻辑
    resumed_session_id = None
    if resume_title:
        # 通过标题恢复
        resumed_session_id = db.resolve_session_by_title(resume_title)
        if resumed_session_id:
            print(f"[恢复] 通过标题 '{resume_title}' 找到会话: {resumed_session_id[:8]}...")
        else:
            print(f"[警告] 未找到标题为 '{resume_title}' 的会话，创建新会话")
    elif resume:
        if resume == "latest":
            # 恢复最近会话
            sessions = jsonl_store.list_sessions()
            if sessions:
                # 按文件修改时间排序，取最新的
                session_files = [(s, jsonl_store._get_file_path(s).stat().st_mtime) for s in sessions]
                session_files.sort(key=lambda x: x[1], reverse=True)
                resumed_session_id = session_files[0][0]
                print(f"[恢复] 最近会话: {resumed_session_id[:8]}...")
            else:
                print("[警告] 没有历史会话，创建新会话")
        else:
            # 按 ID 恢复
            if jsonl_store.session_exists(resume):
                resumed_session_id = resume
                print(f"[恢复] 会话: {resumed_session_id[:8]}...")
            else:
                print(f"[警告] 会话 {resume[:8]}... 不存在，创建新会话")

    if resumed_session_id:
        session_id = resumed_session_id
        db.reopen_session(session_id)
        # 加载 JSONL 历史
        history = jsonl_store.load_messages(session_id)
        print(f"[历史] 加载 {len(history)} 条消息")
    else:
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

    # 设置消息追加回调，实时保存所有消息（包括 tool 消息）到 JSONL
    def _on_message_append(msg: dict[str, Any]) -> None:
        role = msg.get("role", "")
        jsonl_store.append_message(
            session_id,
            role=role,
            content=msg.get("content"),
            tool_calls=msg.get("tool_calls"),
            tool_call_id=msg.get("tool_call_id"),
        )

    loop.set_on_message_append(_on_message_append)

    # 获取工具 schema
    from src.tools.registry import get_tool_schemas
    tool_schemas = get_tool_schemas()

    # ========================================================================
    # 7. 启动交互
    # ========================================================================
    system_prompt = assembler.assemble()

    # 如果恢复了会话，加载 JSONL 历史作为消息
    if resumed_session_id:
        history = jsonl_store.load_messages(session_id)
        # 过滤掉 system 消息（我们已有新的 system_prompt）
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = msg.get("role")
            if role == "system":
                continue
            # 重建 OpenAI 格式的消息
            openai_msg = {"role": role}
            if "content" in msg:
                openai_msg["content"] = msg["content"]
            if "tool_calls" in msg:
                openai_msg["tool_calls"] = msg["tool_calls"]
            if "tool_call_id" in msg:
                openai_msg["tool_call_id"] = msg["tool_call_id"]
            messages.append(openai_msg)
        print(f"[历史] 已加载 {len(history)} 条消息")
    else:
        messages = [{"role": "system", "content": system_prompt}]

    resume_hint = " (已恢复历史)" if resumed_session_id else ""
    print("=" * 50)
    print(f"  NanoHermes v0.1.0 - 交互对话模式{resume_hint}")
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

        # 保存用户消息到 SQLite 和 JSONL
        db.insert_message(session_id, "user", user_input)
        jsonl_store.append_message(session_id, "user", user_input)
        messages.append({"role": "user", "content": user_input})

        print("\n[思考中]...", end="", flush=True)

        try:
            # 运行对话循环（包含工具调用链）
            result = loop.run(messages, tool_schemas if tool_schemas else None)

            content = result.get("final_response", "")
            iterations = result.get("iterations", 0)
            usage = result.get("usage")

            # 保存助手消息到 SQLite（JSONL 通过 on_message_append 回调自动保存）
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
    parser.add_argument("--resume", nargs="?", const="latest", metavar="SESSION_ID",
                        help="恢复历史会话。不指定 ID 时恢复最近会话，或指定 SESSION_ID")
    parser.add_argument("--resume-title", metavar="TITLE",
                        help="通过标题恢复历史会话")
    args = parser.parse_args()

    if args.test_api:
        test_api()
    else:
        interactive_mode(debug=args.debug, resume=args.resume, resume_title=args.resume_title)


if __name__ == "__main__":
    main()
