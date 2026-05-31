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

from dotenv import load_dotenv  # noqa: F401 - kept for backward compatibility


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
    from src.config import load_config, get_api_key, get_base_url

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = config.model.name

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


def main_chat(debug: bool = False, resume: str | None = None, resume_title: str | None = None):
    """运行 TUI 聊天界面（默认交互模式）。

    Args:
        debug: 是否开启 debug 模式。
        resume: 恢复会话 ID。
        resume_title: 通过标题恢复会话。
    """
    from src.config import load_config, get_api_key, get_base_url

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = config.model.name

    if not api_key:
        print("[错误] 未设置 API Key，请检查 .env 或配置文件")
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
    
    # 按工具集分类工具
    tool_categories = {}
    for tool in ToolRegistry.get_all_tools():
        category = tool.toolset
        if category not in tool_categories:
            tool_categories[category] = []
        tool_categories[category].append(tool.name)

    # 获取技能数量
    from src.skills.manager import SkillManager
    skill_manager = SkillManager()
    skill_count = len(skill_manager.list_skills())
    
    # 按类别分类技能
    skill_categories = {}
    for entry in skill_manager.list_skills():
        # 从路径推断类别
        path = entry.skill.path
        if "/skills/" in path:
            parts = path.split("/skills/")[1].split("/")
            if len(parts) >= 2:
                category = parts[0]
            else:
                category = "other"
        else:
            category = "other"
        
        if category not in skill_categories:
            skill_categories[category] = []
        skill_categories[category].append(entry.skill.name)

    # 会话 ID
    session_id = "new_session"

    # 初始化 SessionDB
    from src.session.session_db import SessionDB
    from pathlib import Path
    db_path = Path.home() / ".nanohermes" / "sessions.db"
    session_db = SessionDB(db_path)

    # 使用 TUI v2
    from src.cli.tui import create_tui_v2
    adapter = create_tui_v2(
        model_caller=model_caller,
        tool_dispatch=tool_dispatch_func,
        model=model,
        session_id=session_id,
        tool_count=tool_count,
        skill_count=skill_count,
        tool_schemas=tool_schemas,
        tool_categories=tool_categories,
        skill_categories=skill_categories,
        config={
            "typing_speed": config.tui.typing_speed,
            "show_tool_panel": config.tui.show_tool_panel,
            "tool_panel_position": config.tui.tool_panel_position,
        },
        session_db=session_db,
    )
    
    # 运行 TUI v2（异步）
    import asyncio
    asyncio.run(adapter.run())


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
    args = parser.parse_args()

    if args.test_api:
        test_api()
    elif args.list_sessions:
        list_sessions_command()
    else:
        main_chat(
            debug=args.debug,
            resume=args.resume,
            resume_title=args.resume_title,
        )


if __name__ == "__main__":
    main()
