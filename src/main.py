"""NanoHermes 主入口。

启动方式:
    python -m src.main              # 交互模式
    python -m src.main --debug      # debug 模式，输出 DEBUG 级别日志

设计理由：
本文件作为组合根（Composition Root），负责解析命令行参数并创建 TUIApp。
所有依赖初始化逻辑已移至 TUIApp._init_dependencies()，本文件保持精简。

注意：
- 本文件不包含业务逻辑，仅负责参数解析和模块组装入口
- 配置加载和模块初始化由 TUIApp 内部完成
"""

import argparse
import asyncio

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
    组合根入口，创建 TUIApp 并运行。所有依赖初始化由 TUIApp 内部完成。

    Args:
        debug: 是否开启 debug 模式（输出完整请求/响应 JSON + 思考内容）。
        resume: 恢复会话 ID（"latest" 表示最近会话）。
        resume_title: 通过标题恢复会话。
    """
    from src.cli.tui import create_tui

    app = create_tui(debug=debug, resume=resume, resume_title=resume_title)
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        # 用户按下 Ctrl+C，优雅退出
        pass


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
    parser.add_argument("--headless", action="store_true",
                        help="Headless REPL 模式（无 TUI，适合管道脚本/SSH/CI）")
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
