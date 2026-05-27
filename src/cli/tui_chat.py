"""NanoHermes TUI - 现代化聊天界面。

基于 rich 和 prompt_toolkit 实现，包含：
- 顶部横幅（模型、工具、技能、会话信息）
- 对话输出区域（流式显示工具调用和响应）
- 底部固定输入区（支持斜杠命令自动补全）
"""

from __future__ import annotations

import sys
from typing import Any, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

# ============================================================================
# 斜杠命令自动补全
# ============================================================================
SLASH_COMMANDS = [
    "/clear", "/status", "/sessions", "/title",
    "/skills", "/skills enable", "/skills disable",
    "/tools", "/quit", "/exit",
]


class SlashCommandCompleter(Completer):
    """斜杠命令自动补全器。"""

    def get_completions(
        self, document: Document, complete_event
    ) -> list[Completion]:
        text = document.text_before_cursor
        if text.startswith("/"):
            for cmd in SLASH_COMMANDS:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text))


# ============================================================================
# TUI 样式
# ============================================================================
TUI_STYLE = Style.from_dict({
    "prompt": "#00ff00 bold",
    "input": "#ffffff",
})

# ============================================================================
# TUI 聊天界面
# ============================================================================
class TUIChat:
    """现代化 TUI 聊天界面。

    Attributes:
        console: rich Console 实例。
        session: prompt_toolkit PromptSession 实例。
        banner_text: 横幅文本。
        conversation_lines: 对话输出行列表。
    """

    def __init__(self, model: str, session_id: str, tool_count: int, skill_count: int):
        """初始化 TUI 聊天界面。

        Args:
            model: 模型名称。
            session_id: 会话 ID。
            tool_count: 工具数量。
            skill_count: 技能数量。
        """
        self.console = Console()
        self.history = InMemoryHistory()
        self.session = PromptSession(
            history=self.history,
            completer=SlashCommandCompleter(),
            style=TUI_STYLE,
        )
        self.model = model
        self.session_id = session_id
        self.tool_count = tool_count
        self.skill_count = skill_count
        self.conversation_lines: list[Text] = []

    def _render_banner(self) -> Panel:
        """渲染顶部横幅。"""
        banner_text = Text()
        banner_text.append("NANOHERMES AGENT", style="bold yellow")
        banner_text.append("\n\n")
        banner_text.append(f"Model: {self.model}\n", style="dim")
        banner_text.append(f"Tools: {self.tool_count}  ", style="dim")
        banner_text.append(f"Skills: {self.skill_count}  ", style="dim")
        banner_text.append(f"Session: {self.session_id[:16]}...", style="dim")

        return Panel(banner_text, title="NanoHermes CLI", border_style="yellow")

    def _render_conversation(self) -> Panel:
        """渲染对话输出区域。"""
        conversation_text = Text()
        conversation_text.append("Conversation output\n\n", style="dim")

        for line in self.conversation_lines:
            conversation_text.append(line)
            conversation_text.append("\n")

        return Panel(conversation_text, title="Conversation", border_style="blue")

    def _render_input_prompt(self) -> str:
        """渲染输入提示符。"""
        return "> "

    def print_banner(self) -> None:
        """打印初始横幅。"""
        self.console.print(self._render_banner())
        self.console.print()
        self.console.print("Type /quit to exit, /clear to clear history")
        self.console.print("Type /help for available commands")
        self.console.print()

    def add_message(self, role: str, content: str, is_tool: bool = False) -> None:
        """添加消息到对话区域。

        Args:
            role: 消息角色（user/assistant/tool）。
            content: 消息内容。
            is_tool: 是否为工具调用。
        """
        line = Text()
        if is_tool:
            line.append(f"⚡ {content}", style="cyan")
        elif role == "user":
            line.append(f"> {content}", style="green")
        elif role == "assistant":
            line.append(f"Hermes: {content}", style="white")
        else:
            line.append(content, style="dim")

        self.conversation_lines.append(line)

    def get_input(self) -> str:
        """获取用户输入。

        Returns:
            用户输入的文本。
        """
        try:
            return self.session.prompt(self._render_input_prompt())
        except (EOFError, KeyboardInterrupt):
            return "/quit"

    def clear_conversation(self) -> None:
        """清空对话区域。"""
        self.conversation_lines.clear()

    def run(self) -> None:
        """运行 TUI 主循环。"""
        self.print_banner()

        while True:
            user_input = self.get_input()

            if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
                self.console.print("\n[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "/clear":
                self.clear_conversation()
                self.console.print("[dim]Conversation cleared.[/dim]")
                continue

            if user_input.lower() == "/help":
                self.console.print("\n[cyan]Available commands:[/cyan]")
                for cmd in SLASH_COMMANDS:
                    self.console.print(f"  {cmd}")
                continue

            # 添加用户消息
            self.add_message("user", user_input)

            # 这里应该调用对话循环，现在只是模拟
            self.add_message("assistant", "This is a simulated response.", is_tool=False)

            # 刷新显示
            self.console.print(self._render_banner())
            self.console.print()
            self.console.print(self._render_conversation())
            self.console.print()
