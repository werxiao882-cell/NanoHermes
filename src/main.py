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
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def list_sessions_command():
    """列出所有历史会话。"""
    from src.session.jsonl_store import JsonlSessionStore
    from src.session.session_db import SessionDB

    jsonl_store = JsonlSessionStore()
    session_ids = jsonl_store.list_sessions()

    if not session_ids:
        print("[信息] 没有历史会话")
        return

    # 按修改时间排序
    session_files = []
    for sid in session_ids:
        file_path = jsonl_store._get_file_path(sid)
        mtime = file_path.stat().st_mtime
        msg_count = jsonl_store.get_message_count(sid)
        session_files.append((sid, mtime, msg_count))

    session_files.sort(key=lambda x: x[1], reverse=True)

    print(f"\n{'='*60}")
    print(f"  历史会话列表 ({len(session_files)} 个)")
    print(f"{'='*60}")

    for i, (sid, mtime, msg_count) in enumerate(session_files, 1):
        from datetime import datetime
        time_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

        # 尝试从 SQLite 获取标题
        title = None
        try:
            db_path = Path.home() / ".nanohermes" / "sessions.db"
            if db_path.exists():
                db = SessionDB(db_path)
                session_info = db.get_session(sid)
                if session_info:
                    title = session_info.get("title")
                db.close()
        except Exception:
            pass

        display_title = title or f"会话 {sid[:8]}"
        print(f"  {i:2d}. {_bold(display_title)}")
        print(f"      ID: {sid}")
        print(f"      时间: {time_str}  |  消息: {msg_count} 条")
        print()

    print(f"{'='*60}")
    print(f"  恢复: python -m src.main --resume <ID>")
    print(f"  恢复最近: python -m src.main --resume")
    print(f"{'='*60}\n")


def generate_auto_title(client, model: str, first_message: str) -> str | None:
    """使用大模型自动生成会话标题。

    Args:
        client: OpenAI SDK 客户端。
        model: 模型名称。
        first_message: 用户的第一条消息。

    Returns:
        生成的标题（≤20 字符），失败返回 None。
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个标题生成器。根据用户的输入，生成一个简短的会话标题，不超过 20 个字符。只输出标题，不要输出其他内容。"},
                {"role": "user", "content": first_message[:200]},
            ],
            max_tokens=20,
            temperature=0.7,
        )
        title = response.choices[0].message.content
        if title:
            # 清理标题
            title = title.strip().strip('"').strip("'").strip()
            if len(title) > 20:
                title = title[:20]
            return title if title else None
    except Exception:
        pass
    return None


def generate_auto_title_async(
    client,
    model: str,
    first_message: str,
    db,
    session_id: str,
) -> threading.Thread:
    """异步生成会话标题，不阻塞对话。

    如果标题生成失败，使用用户首条消息的截取部分作为标题。

    Args:
        client: OpenAI SDK 客户端。
        model: 模型名称。
        first_message: 用户的第一条消息。
        db: SessionDB 实例。
        session_id: 会话 ID。

    Returns:
        后台线程。
    """

    def _title_task():
        """后台标题生成任务。"""
        try:
            title = generate_auto_title(client, model, first_message)
            if title:
                db.set_session_title(session_id, title)
                print(f"\r[标题] {title}          ")  # 覆盖之前的提示
            else:
                # 生成失败，使用截取的首条消息
                fallback = first_message[:20].strip()
                if fallback:
                    db.set_session_title(session_id, fallback)
                    print(f"\r[标题] {fallback}          ")
        except Exception:
            # 完全失败，使用截取的首条消息
            fallback = first_message[:20].strip()
            if fallback:
                try:
                    db.set_session_title(session_id, fallback)
                except Exception:
                    pass
                print(f"\r[标题] {fallback}          ")

    thread = threading.Thread(target=_title_task, daemon=True)
    thread.start()
    return thread
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


def run_tui_mode(debug: bool = False, resume: str | None = None, resume_title: str | None = None):
    """运行现代化 TUI 聊天界面。

    Args:
        debug: 是否开启 debug 模式。
        resume: 恢复会话 ID。
        resume_title: 通过标题恢复会话。
    """
    load_dotenv()

    api_key = os.environ.get("DASHSCOPE_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    model = os.environ.get("MODEL_NAME", "qwen3.6-plus")

    if not api_key:
        print("[错误] 未设置 API Key，请在 .env 文件中配置")
        sys.exit(1)

    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    model_caller = build_model_caller(client, model)

    # 初始化工具
    from src.tools import terminal
    from src.tools import file_tools
    from src.tools import clarify_tools
    from src.tools import code_execution_tools
    from src.tools import cronjob_tools
    from src.tools import delegation_tools
    from src.tools import memory_tools
    from src.tools import session_search_tools
    from src.tools import skills_tools
    from src.tools import process_tools
    from src.tools import todo_tools
    from src.tools.registry import ToolRegistry
    from src.tools.dispatcher import dispatch as tool_dispatch_func
    from src.tools.registry import get_tool_schemas

    tool_count = len(ToolRegistry.get_all_tools())
    tool_schemas = get_tool_schemas()

    # 获取技能数量
    from src.skills.manager import SkillManager
    skill_manager = SkillManager()
    skill_count = len(skill_manager.list_skills())

    # 会话 ID
    session_id = "new_session"

    # 启动 TUI
    from src.cli.tui_chat import TUIChat
    tui = TUIChat(
        model=model,
        session_id=session_id,
        tool_count=tool_count,
        skill_count=skill_count,
        model_caller=model_caller,
        tool_dispatch=tool_dispatch_func,
        tool_schemas=tool_schemas,
    )
    tui.run()


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
    from src.tools import terminal  # noqa: F401
    from src.tools import file_tools  # noqa: F401
    from src.tools import clarify_tools  # noqa: F401
    from src.tools import code_execution_tools  # noqa: F401
    from src.tools import cronjob_tools  # noqa: F401
    from src.tools import delegation_tools  # noqa: F401
    from src.tools import memory_tools  # noqa: F401
    from src.tools import session_search_tools  # noqa: F401
    from src.tools import skills_tools  # noqa: F401
    from src.tools import process_tools  # noqa: F401
    from src.tools import todo_tools  # noqa: F401
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

    # ========================================================================
    # 5.5 初始化 Skill System - 技能管理
    # ========================================================================
    from src.skills.manager import SkillManager

    skill_manager = SkillManager()
    skills_prompt = skill_manager.build_skill_prompt()

    # 组装 stable 层（身份 + 工具 + 记忆 + 技能）
    stable_parts = [
        "你是 NanoHermes，一个有用的 AI 助手。",
        "你可以使用终端工具执行命令。",
    ]
    if memory_context:
        stable_parts.append(memory_context)
    if skills_prompt:
        stable_parts.append(skills_prompt)
    assembler.set_stable(stable_parts)

    # ========================================================================
    # 6. 初始化 Conversation Loop - 核心对话循环
    # ========================================================================
    from src.conversation.loop import ConversationLoop
    from src.conversation.error_classifier import ErrorCategory

    # 工具进度回调
    def _on_tool_start(tool_name: str, args: str) -> None:
        """工具开始执行时的回调。"""
        print(f"│ 🟦 preparing {tool_name}...")

    def _on_tool_end(tool_name: str, args: str, result: str, elapsed: float) -> None:
        """工具结束执行时的回调。"""
        # 格式化参数显示
        try:
            import json
            args_dict = json.loads(args) if args else {}
            # 取第一个值作为动作描述，如果没有则用 'exec'
            action = next(iter(args_dict.values())) if args_dict else "exec"
            if isinstance(action, dict):
                action = "exec"
            elif len(str(action)) > 20:
                action = str(action)[:20] + "..."
        except Exception:
            action = "exec"

        print(f"│ 🟦 {tool_name}   {action} {elapsed:.1f}s")

    loop = ConversationLoop(
        max_iterations=90,
        model_call=model_caller,
        tool_dispatch=tool_dispatch_func,
        debug=debug,
        on_tool_start=_on_tool_start,
        on_tool_end=_on_tool_end,
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
    print("  输入 '/clear' 清空对话")
    print("  输入 '/status' 查看会话状态")
    print("  输入 '/sessions' 查看历史会话列表")
    print("  输入 '/title <标题>' 设置当前会话标题")
    print("  输入 '/skills' 查看可用技能")
    print("  输入 '/skills enable <名称>' 启用技能")
    print("  输入 '/skills disable <名称>' 禁用技能")
    print("  输入 '/tools' 查看已加载工具")
    print("=" * 50)

    # 跟踪是否已经自动生成标题
    auto_title_generated = resumed_session_id is not None

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[退出] 再见!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("[退出] 再见!")
            break

        # /clear 清空对话
        if user_input.lower() == "/clear":
            messages = [messages[0]]  # 保留 system message
            print("[清空] 对话已清空")
            continue

        # /status 查看会话状态
        if user_input.lower() == "/status":
            session_info = db.get_session(session_id)
            if session_info:
                title = session_info.get("title") or "(未设置)"
                print(f"[状态] 会话: {session_id}")
                print(f"       标题: {title}")
                print(f"       模型: {session_info.get('model', 'N/A')}")
                print(f"       输入 Token: {session_info.get('input_tokens', 0)}")
                print(f"       输出 Token: {session_info.get('output_tokens', 0)}")
            continue

        # /sessions 查看历史会话列表
        if user_input.lower() == "/sessions":
            list_sessions_command()
            continue

        # /title 设置会话标题
        if user_input.lower().startswith("/title "):
            new_title = user_input[7:].strip()
            if new_title:
                db.set_session_title(session_id, new_title)
                print(f"[标题] 已设置为: {new_title}")
            continue

        # /skills 查看可用技能
        if user_input.lower() == "/skills":
            entries = skill_manager.list_skills()
            if not entries:
                print("[技能] 没有已加载的技能")
            else:
                print(f"\n[技能] 可用技能 ({len(entries)} 个):")
                for e in entries:
                    status = "✓" if e.enabled else "✗"
                    print(f"  {status} {e.skill.name}: {e.skill.description}")
                print()
            continue

        # /skills enable 启用技能
        if user_input.lower().startswith("/skills enable "):
            name = user_input[15:].strip()
            if skill_manager.enable_skill(name):
                print(f"[技能] 已启用: {name}")
            else:
                print(f"[技能] 未找到: {name}")
            continue

        # /skills disable 禁用技能
        if user_input.lower().startswith("/skills disable "):
            name = user_input[16:].strip()
            if skill_manager.disable_skill(name):
                print(f"[技能] 已禁用: {name}")
            else:
                print(f"[技能] 未找到: {name}")
            continue

        # /tools 查看已加载工具
        if user_input.lower() == "/tools":
            from src.tools.registry import ToolRegistry
            tools = ToolRegistry.get_all_tools()
            if not tools:
                print("[工具] 没有已加载的工具")
            else:
                print(f"\n[工具] 已加载工具 ({len(tools)} 个):")
                for t in tools:
                    print(f"  ⚡ {t.name} ({t.toolset}): {t.description or t.schema.get('description', '')[:80]}")
                print()
            continue

        if not user_input:
            continue

        # 保存用户消息到 SQLite 和 JSONL
        db.insert_message(session_id, "user", user_input)
        jsonl_store.append_message(session_id, "user", user_input)
        messages.append({"role": "user", "content": user_input})

        # 自动生成标题（异步，不阻塞对话）
        if not auto_title_generated and not resumed_session_id:
            auto_title_generated = True
            print("\n[生成标题]...", end="", flush=True)
            # 异步生成标题，失败时使用首条消息截取
            generate_auto_title_async(client, model, user_input, db, session_id)

        print("\n[思考中]...", end="", flush=True)

        try:
            # 运行对话循环（包含工具调用链）
            result = loop.run(messages, tool_schemas if tool_schemas else None)

            content = result.get("final_response", "")
            iterations = result.get("iterations", 0)
            usage = result.get("usage")

            # 检查是否有 clarify 工具调用
            from src.tools.clarify_tools import get_pending_clarification, respond_to_clarification, clear_pending_clarification
            pending = get_pending_clarification()

            if pending and pending.get("status") == "pending":
                # 显示澄清问题
                print(f"\n{'='*50}")
                print(f"  💬 {pending['question']}")
                print(f"{'='*50}")

                options = pending.get("options", [])
                allow_custom = pending.get("allow_custom", True)

                # 显示选项
                for i, opt in enumerate(options, 1):
                    print(f"  {i}. {opt}")

                if allow_custom:
                    print(f"  0. 自定义输入")

                print()

                # 获取用户输入
                while True:
                    choice = input("  请选择 (数字或输入): ").strip()

                    # 检查是否选择预设选项
                    if choice.isdigit():
                        idx = int(choice)
                        if idx == 0 and allow_custom:
                            # 自定义输入
                            custom = input("  请输入: ").strip()
                            if custom:
                                respond_to_clarification(custom)
                                break
                        elif 1 <= idx <= len(options):
                            respond_to_clarification(options[idx - 1])
                            break
                        else:
                            print(f"  无效选项，请选择 1-{len(options)} 或 0")
                    else:
                        # 自定义输入
                        if allow_custom and choice:
                            respond_to_clarification(choice)
                            break
                        else:
                            print("  请输入数字或自定义内容")

                clear_pending_clarification()

                # 将用户回答作为新消息继续对话
                user_response = pending.get("response", "")
                messages.append({
                    "role": "user",
                    "content": f"[Clarify Response] {user_response}"
                })

                # 继续运行对话循环
                print("\n[继续思考中]...", end="", flush=True)
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
    parser.add_argument("--list-sessions", action="store_true",
                        help="列出所有历史会话")
    parser.add_argument("--tui", action="store_true",
                        help="启动现代化 TUI 聊天界面")
    args = parser.parse_args()

    if args.test_api:
        test_api()
    elif args.list_sessions:
        list_sessions_command()
    elif args.tui:
        run_tui_mode(debug=args.debug, resume=args.resume, resume_title=args.resume_title)
    else:
        interactive_mode(debug=args.debug, resume=args.resume, resume_title=args.resume_title)


if __name__ == "__main__":
    main()
