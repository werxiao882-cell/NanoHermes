"""NanoHermes TUI - 现代化聊天界面。

基于 rich 和 prompt_toolkit 实现，包含：
- 顶部横幅（模型、工具、技能、会话信息）
- 对话输出区域（流式显示工具调用和响应）
- 底部固定输入区（支持斜杠命令自动补全）
- 工具调用进度显示
- 实际对话循环集成
"""

from __future__ import annotations

import sys
import time
import json
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
from rich.status import Status

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

    def __init__(
        self,
        model: str,
        session_id: str,
        tool_count: int,
        skill_count: int,
        model_caller: Callable | None = None,
        tool_dispatch: Callable | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
    ):
        """初始化 TUI 聊天界面。

        Args:
            model: 模型名称。
            session_id: 会话 ID。
            tool_count: 工具数量。
            skill_count: 技能数量。
            model_caller: 模型调用函数。
            tool_dispatch: 工具分发函数。
            tool_schemas: 工具 schema 列表。
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
        self.model_caller = model_caller
        self.tool_dispatch = tool_dispatch
        self.tool_schemas = tool_schemas or []
        self.messages: list[dict[str, Any]] = []

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

    def show_tool_start(self, tool_name: str, action: str) -> None:
        """显示工具开始执行。

        Args:
            tool_name: 工具名称。
            action: 工具动作/参数。
        """
        self.console.print(f"│ 🟦 preparing {tool_name}...", style="dim")

    def show_tool_complete(self, tool_name: str, action: str, elapsed: float) -> None:
        """显示工具执行完成。

        Args:
            tool_name: 工具名称。
            action: 工具动作/参数。
            elapsed: 执行时间（秒）。
        """
        self.console.print(f"│ 🟦 {tool_name}  {action} {elapsed:.1f}s", style="dim")

    def show_tool_result_summary(self, tool_name: str, result: str) -> None:
        """显示工具调用简要结果。

        Args:
            tool_name: 工具名称。
            result: 工具执行结果（JSON 字符串）。
        """
        try:
            data = json.loads(result)
            if tool_name == "read_file":
                lines = data.get("content", "").count("\n") + 1
                self.console.print(f"│ 📄 read_file: {lines} lines read", style="dim")
            elif tool_name == "write_file":
                bytes_written = data.get("bytes_written", 0)
                self.console.print(f"│ 📝 write_file: {bytes_written} bytes written", style="dim")
            elif tool_name == "search_files":
                count = data.get("total_found", 0)
                self.console.print(f"│ 🔍 search_files: {count} files found", style="dim")
            elif tool_name == "terminal":
                exit_code = data.get("exit_code", -1)
                self.console.print(f"│ 💻 terminal: exit code {exit_code}", style="dim")
            else:
                self.console.print(f"│ ✅ {tool_name}: completed", style="dim")
        except (json.JSONDecodeError, AttributeError):
            self.console.print(f"│ ✅ {tool_name}: completed", style="dim")

    def show_separator(self, agent_name: str = "NanoHermes") -> None:
        """显示代理响应分隔符。

        Args:
            agent_name: 代理名称。
        """
        self.console.print(f"┌─ {agent_name} " + "─" * 50, style="bold yellow")

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
        self.messages = [m for m in self.messages if m.get("role") == "system"]

    def _run_conversation_loop(self, user_input: str) -> None:
        """运行实际对话循环。

        Args:
            user_input: 用户输入。
        """
        if not self.model_caller or not self.tool_dispatch:
            # Fallback to mock if no caller/dispatch
            self.add_message("assistant", "This is a simulated response.", is_tool=False)
            return

        # Add user message
        self.messages.append({"role": "user", "content": user_input})

        max_iterations = 10
        for iteration in range(max_iterations):
            # Call model
            with self.console.status("[dim]Thinking...[/dim]", spinner="dots"):
                response = self.model_caller(self.messages, self.tool_schemas if self.tool_schemas else None)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")

            if tool_calls:
                # Process tool calls
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", "{}")

                    # Show tool start
                    try:
                        args_dict = json.loads(tool_args)
                        action = next(iter(args_dict.values())) if args_dict else "exec"
                        if isinstance(action, dict):
                            action = "exec"
                        elif len(str(action)) > 20:
                            action = str(action)[:20] + "..."
                    except (json.JSONDecodeError, StopIteration):
                        action = "exec"

                    self.show_tool_start(tool_name, action)

                    # Execute tool
                    start_time = time.time()
                    result = self.tool_dispatch(tool_name, tool_args)
                    elapsed = time.time() - start_time

                    # Show tool complete and result summary
                    self.show_tool_complete(tool_name, action, elapsed)
                    self.show_tool_result_summary(tool_name, result)

                    # Add tool result to messages
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    })

                continue

            # No tool calls, show response
            if content:
                self.show_separator()
                self.console.print(content)
                self.console.print()
                self.messages.append({"role": "assistant", "content": content})
            break

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

            # Add user message to display
            self.add_message("user", user_input)

            # Run actual conversation loop
            self._run_conversation_loop(user_input)

            # Refresh display
            self.console.print(self._render_banner())
            self.console.print()
            self.console.print(self._render_conversation())
            self.console.print()
