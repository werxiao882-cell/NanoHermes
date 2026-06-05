"""NanoHermes 主入口。

启动方式:
    python -m src.main              # 交互模式
    python -m src.main --debug      # debug 模式，输出 DEBUG 级别日志

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
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv  # noqa: F401 - kept for backward compatibility


def _bold(text: str) -> str:
    """终端加粗文本（ANSI 转义码）。"""
    return f"\033[1m{text}\033[0m"


def list_sessions_command():
    """列出所有历史会话。"""
    from src.session.session_db import get_sessions_list_for_display

    sessions = get_sessions_list_for_display()

    if not sessions:
        print("[信息] 没有历史会话")
        return

    print(f"\n{'='*60}")
    print(f"  历史会话列表 ({len(sessions)} 个)")
    print(f"{'='*60}")

    for i, session in enumerate(sessions, 1):
        print(f"  {i:2d}. {_bold(session['title'])}")
        print(f"      ID: {session['session_id']}")
        print(f"      时间: {session['time_str']}  |  消息: {session['msg_count']} 条")
        print()

    print(f"{'='*60}")
    print(f"  恢复: python -m src.main --resume <ID>")
    print(f"  恢复最近: python -m src.main --resume")
    print(f"{'='*60}\n")


def main_chat(debug: bool = False, resume: str | None = None, resume_title: str | None = None):
    """运行 TUI 聊天界面（默认交互模式）。

    Args:
        debug: 是否开启 debug 模式。
        resume: 恢复会话 ID。
        resume_title: 通过标题恢复会话。
    """
    # 配置日志级别（仅对 src 命名空间启用 DEBUG，不影响第三方库）
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if debug:
        logging.getLogger("src").setLevel(logging.DEBUG)

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

    from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
    provider_client = ProviderOpenAIClient(client, model)
    model_caller = provider_client.build_caller()

    # 初始化工具
    from src.tools.registry import ToolRegistry
    from src.tools.dispatcher import dispatch as tool_dispatch_func

    ToolRegistry.init_all_tools()

    tool_count = len(ToolRegistry.get_all_tools())
    tool_schemas = ToolRegistry.get_tool_schemas()
    tool_categories = ToolRegistry.get_tool_categories()

    # 获取技能数量
    from src.skills.manager import SkillManager
    skill_manager = SkillManager()
    skill_count = len(skill_manager.list_skills())
    
    # 按类别分类技能
    skill_categories = skill_manager.get_skills_by_category()

    # 会话 ID
    session_id = "new_session"

    # 初始化 SessionDB 和 JsonlSessionStore
    from src.session.session_db import SessionDB
    from src.session.jsonl_store import JsonlSessionStore
    from pathlib import Path
    db_path = Path.home() / ".nanohermes" / "sessions.db"
    session_db = SessionDB(db_path)
    jsonl_store = JsonlSessionStore()

    # 初始化 MemoryManager
    from src.memory import MemoryManager, FileMemoryProvider
    memory_manager = MemoryManager()
    hermes_home = str(Path.home() / ".nanohermes")
    file_provider = FileMemoryProvider(hermes_home)
    memory_manager.add_provider(file_provider)

    # 使用 TUI
    from src.cli.tui import create_tui
    app = create_tui(
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
        jsonl_store=jsonl_store,
        memory_manager=memory_manager,
        skill_manager=skill_manager,
        debug=debug,
    )
    
    # 运行 TUI（异步）
    import asyncio
    asyncio.run(app.run())


def main():
    """主入口函数。"""
    parser = argparse.ArgumentParser(description="NanoHermes - 自进化 AI Agent 系统")
    parser.add_argument("--debug", action="store_true", help="开启 debug 模式，输出请求/响应详情")
    parser.add_argument("--resume", nargs="?", const="latest", metavar="SESSION_ID",
                        help="恢复历史会话。不指定 ID 时恢复最近会话，或指定 SESSION_ID")
    parser.add_argument("--resume-title", metavar="TITLE",
                        help="通过标题恢复历史会话")
    parser.add_argument("--list-sessions", action="store_true",
                        help="列出所有历史会话")
    args = parser.parse_args()

    if args.list_sessions:
        list_sessions_command()
    else:
        main_chat(
            debug=args.debug,
            resume=args.resume,
            resume_title=args.resume_title,
        )


if __name__ == "__main__":
    main()
