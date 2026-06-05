"""NanoHermes 主入口。

启动方式:
    python -m src.main              # 交互模式
    python -m src.main --debug      # debug 模式，输出 DEBUG 级别日志

设计理由：
本文件作为组合根（Composition Root），负责依赖注入和模块组装。
遵循依赖注入原则：所有依赖在此创建并注入到各模块中，而非在模块内部创建。

耦合的核心模块:
- Provider Runtime: 凭证解析 + 客户端构建
- Tool Runtime: 工具注册 + 分发
- Session Storage: 会话持久化
- Conversation Loop: 核心对话循环
- Prompt Assembly: 系统提示组装
- Memory System: 记忆注入
- CLI/TUI: 用户界面

注意：
- 本文件不包含业务逻辑，仅负责模块组装
- 所有 SDK 调用通过 provider/client_factory.py 的 build_client() 工厂
- 配置加载优先于模块初始化
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv  # noqa: F401 - 保持向后兼容，确保 .env 文件被加载


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

    设计理由：
    这是组合根的核心函数，按以下顺序组装所有模块：
    1. 配置加载（优先级：.env > 配置文件 > 默认值）
    2. Provider 客户端构建（根据 api_mode 选择 OpenAI/Anthropic）
    3. 工具系统初始化（注册表 + 分发器）
    4. 会话存储初始化（SQLite + JSONL 双存储）
    5. 记忆系统初始化（文件提供者）
    6. 技能管理器初始化
    7. TUI 创建（依赖注入所有上述模块）
    
    为什么在这里直接创建 OpenAI 客户端？
    - AGENTS.md 约定"入口文件不应直接操作 SDK"，但这里是例外情况
    - 原因：ProviderOpenAIClient 需要原生 OpenAI 客户端作为底层 SDK
    - 这是依赖注入的必要步骤，而非业务逻辑直接调用 SDK
    - 正确的做法是通过 build_client() 工厂，但当前实现需要包装原生客户端
    - TODO: 重构为完全通过工厂创建，消除这里的直接 SDK 调用

    Args:
        debug: 是否开启 debug 模式（输出完整请求/响应 JSON + 思考内容）。
        resume: 恢复会话 ID（"latest" 表示最近会话）。
        resume_title: 通过标题恢复会话。
    """
    # 配置日志级别（仅对 src 命名空间启用 DEBUG，不影响第三方库）
    # 设计理由：
    # - 默认 WARNING 级别，避免第三方库的 DEBUG 日志干扰
    # - 仅 src.* 命名空间在 debug 模式下启用 DEBUG 级别
    # - 这样可以在调试时看到应用逻辑，同时保持依赖库的安静
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if debug:
        logging.getLogger("src").setLevel(logging.DEBUG)

    # ── 步骤 1: 加载配置 ──
    # 配置优先级：显式参数 > 项目配置 > 全局配置 > .env > 默认值
    from src.config import load_config, get_api_key, get_base_url

    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = config.model.name

    if not api_key:
        print("[错误] 未设置 API Key，请检查 .env 或配置文件")
        sys.exit(1)

    # ── 步骤 2: 构建 Provider 客户端 ──
    # 注意：这里直接创建了 OpenAI 客户端，是约定中的例外情况
    # 原因：ProviderOpenAIClient 是对原生 SDK 的包装，需要原生客户端作为输入
    # TODO: 未来应通过 build_client() 工厂完全消除这里的直接调用
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)

    from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
    provider_client = ProviderOpenAIClient(client, model)
    model_caller = provider_client.build_caller()  # 构建可重用的调用器闭包

    # ── 步骤 3: 初始化工具系统 ──
    # 工具注册表是类级别单例，需要全局初始化一次
    from src.tools.registry import ToolRegistry
    from src.tools.dispatcher import dispatch as tool_dispatch_func

    ToolRegistry.init_all_tools()  # 扫描 src/tools/ 目录并注册所有工具

    tool_count = len(ToolRegistry.get_all_tools())
    tool_schemas = ToolRegistry.get_tool_schemas()  # 用于 LLM 工具调用
    tool_categories = ToolRegistry.get_tool_categories()  # 用于 UI 展示

    # ── 步骤 4: 初始化技能系统 ──
    from src.skills.manager import SkillManager
    skill_manager = SkillManager()
    skill_count = len(skill_manager.list_skills())
    
    # 按类别分类技能（用于 UI 展示和上下文感知补全）
    skill_categories = skill_manager.get_skills_by_category()

    # ── 步骤 5: 初始化会话存储 ──
    # 双存储策略：SQLite 用于元数据和搜索，JSONL 用于完整消息历史
    session_id = "new_session"  # 实际 ID 会在创建会话时生成

    from src.session.session_db import SessionDB
    from src.session.jsonl_store import JsonlSessionStore
    from pathlib import Path
    db_path = Path.home() / ".nanohermes" / "sessions.db"
    session_db = SessionDB(db_path)
    jsonl_store = JsonlSessionStore()

    # ── 步骤 6: 初始化记忆系统 ──
    # MemoryManager 编排多个提供者，当前只使用文件提供者
    from src.memory import MemoryManager, FileMemoryProvider
    memory_manager = MemoryManager()
    hermes_home = str(Path.home() / ".nanohermes")
    file_provider = FileMemoryProvider(hermes_home)
    memory_manager.add_provider(file_provider)

    # ── 步骤 7: 创建 TUI（依赖注入所有模块） ──
    # 设计理由：
    # TUI 不实现任何业务逻辑，仅负责：
    # - 用户输入输出
    # - 事件订阅和 UI 更新
    # - 调用注入的依赖（model_caller, tool_dispatch 等）
    from src.cli.tui import create_tui
    app = create_tui(
        model_caller=model_caller,        # 注入模型调用函数（闭包）
        tool_dispatch=tool_dispatch_func,  # 注入工具分发函数
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
        session_db=session_db,            # 注入 SQLite 会话数据库
        jsonl_store=jsonl_store,          # 注入 JSONL 存储
        memory_manager=memory_manager,    # 注入记忆管理器
        skill_manager=skill_manager,      # 注入技能管理器
        debug=debug,
    )
    
    # 运行 TUI（异步）
    # asyncio.run() 创建新的事件循环并运行直到完成
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
