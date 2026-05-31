"""TUI 主模块。

合并了 TUIApp 和 TUIV2Adapter，提供完整的 TUI 功能。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.cli.state import TUIState
from src.cli.event_handler import TUIEventHandler
from src.cli.layout import LayoutManager, LayoutConfig
from src.cli.completers import ContextAwareCompleter
from src.cli.history import TUIHistory
from src.cli.streaming import TypewriterEffect, StreamingMarkdown, StreamingStatusIndicator
from src.cli.widgets import StatusBar

logger = logging.getLogger(__name__)

SLASH_COMMANDS = [
    "/clear", "/status", "/sessions", "/title",
    "/skills", "/skills enable", "/skills disable",
    "/tools", "/quit", "/exit",
]


class TUIApp:
    """TUI 主应用类，整合了应用管理和适配器功能。"""

    def __init__(
        self,
        model_caller=None,
        tool_dispatch=None,
        model: str = "",
        session_id: str = "",
        tool_count: int = 0,
        skill_count: int = 0,
        tool_schemas: list[dict[str, Any]] | None = None,
        tool_categories: dict[str, list[str]] | None = None,
        skill_categories: dict[str, list[str]] | None = None,
        config: dict[str, Any] | None = None,
    ):
        self.config = config or {}
        self.state = TUIState()
        self.event_handler = TUIEventHandler(self.state)

        layout_config = LayoutConfig(
            show_tool_panel=self.config.get("show_tool_panel", True),
            tool_panel_position=self.config.get("tool_panel_position", "right"),
        )
        self.layout_manager = LayoutManager(layout_config)

        self.key_bindings = self._create_key_bindings()
        self.style = self._create_style()
        self.completer = ContextAwareCompleter()
        self.history = TUIHistory()
        self.session = PromptSession(
            key_bindings=self.key_bindings,
            style=self.style,
            completer=self.completer,
            history=self.history,
        )
        self.application: Application | None = None

        # 适配器功能
        self.model_caller = model_caller
        self.tool_dispatch = tool_dispatch
        self.model = model
        self.session_id = session_id
        self.tool_count = tool_count
        self.skill_count = skill_count
        self.tool_schemas = tool_schemas or []
        self.tool_categories = tool_categories or {}
        self.skill_categories = skill_categories or {}

        self.console = Console()
        self.conversation_lines: list[Text] = []
        self.messages: list[dict[str, Any]] = []
        self.status_bar = StatusBar(model=model, context_window=1_000_000)
        self.typewriter = TypewriterEffect(speed_ms=self.config.get("typing_speed", 10))
        self.streaming_md = StreamingMarkdown()
        self.status_indicator = StreamingStatusIndicator()

        self.state.session_id = session_id
        logger.info("TUIApp 初始化完成")

    def _create_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("c-d")
        def _(event):
            self.state.running = False
            event.app.exit()

        @bindings.add("c-c")
        def _(event):
            self.event_handler.handle_interrupt()
            self.state.running = False
            event.app.exit()

        return bindings

    def _create_style(self) -> Style:
        return Style.from_dict({
            "input": "#00ff00",
            "input.placeholder": "#006600",
            "user.message": "#00aaff",
            "assistant.message": "#ffffff",
            "system.message": "#888888",
            "tool.start": "#ffaa00",
            "tool.running": "#ffaa00",
            "tool.success": "#00ff00",
            "tool.error": "#ff0000",
            "status.loading": "#ffaa00",
            "status.ready": "#00ff00",
            "panel-border": "#444444",
            "panel.title": "#00aaff",
        })

    # ========================================================================
    # 渲染功能
    # ========================================================================

    def _render_banner(self) -> Panel:
        banner_text = Text()
        banner_text.append("NANOHERMES AGENT", style="bold yellow")
        banner_text.append("\n\n")
        banner_text.append(f"Model: {self.model}\n", style="dim")
        banner_text.append(f"Session: {self.session_id[:16]}...\n\n", style="dim")

        if self.tool_categories:
            banner_text.append("Tools:\n", style="bold cyan")
            for category, tools in sorted(self.tool_categories.items()):
                tool_list = ", ".join(tools[:5])
                if len(tools) > 5:
                    tool_list += f" 等 {len(tools)} 个"
                banner_text.append(f"  • {category}: {tool_list}\n", style="dim")
            banner_text.append("\n", style="dim")

        if self.skill_categories:
            banner_text.append("Skills:\n", style="bold green")
            for category, skills in sorted(self.skill_categories.items()):
                skill_list = ", ".join(skills[:5])
                if len(skills) > 5:
                    skill_list += f" 等 {len(skills)} 个"
                banner_text.append(f"  • {category}: {skill_list}\n", style="dim")

        return Panel(banner_text, title="NanoHermes", border_style="yellow")

    def _render_conversation(self) -> Panel:
        conversation_text = Text()
        for line in self.conversation_lines:
            conversation_text.append(line)
            conversation_text.append("\n")
        return Panel(conversation_text, title="Conversation", border_style="blue")

    def print_banner(self) -> None:
        self.console.print(self._render_banner())
        self.console.print()
        self.console.print("Type /quit to exit, /clear to clear history")
        self.console.print("Type /help for available commands")
        self.console.print()

    def add_message(self, role: str, content: str, is_tool: bool = False) -> None:
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

    def show_reasoning(self, reasoning: str, elapsed_ms: float = 0) -> None:
        if not reasoning:
            return
        if elapsed_ms < 1000:
            time_str = f"{elapsed_ms:.0f}ms"
        else:
            time_str = f"{elapsed_ms / 1000:.1f}s"
        self.console.print(f"[bold orange]+ Thought: {time_str}[/bold orange]")
        preview = reasoning[:50] + "..." if len(reasoning) > 50 else reasoning
        self.console.print(f"[dim]  {preview}[/dim]")
        self.console.print("[dim]  (点击 + 展开完整思考内容)[/dim]")
        self.console.print()

    def show_tool_start(self, tool_name: str, action: str) -> None:
        self.console.print(f"│ 🟦 preparing {tool_name}...", style="dim")

    def show_tool_complete(self, tool_name: str, action: str, elapsed: float) -> None:
        self.console.print(f"│ 🟦 {tool_name}  {action} {elapsed:.1f}s", style="dim")

    def show_tool_result_summary(self, tool_name: str, result: str) -> None:
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
        self.console.print(f"┌─ {agent_name} " + "─" * 50, style="bold yellow")

    def clear_conversation(self) -> None:
        self.conversation_lines.clear()
        self.messages = [m for m in self.messages if m.get("role") == "system"]

    def _print_status_bar(self) -> None:
        self.console.print(self.status_bar.render())
        self.console.print()

    # ========================================================================
    # 对话循环
    # ========================================================================

    async def _run_conversation_loop(self, user_input: str) -> None:
        if not self.model_caller or not self.tool_dispatch:
            self.add_message("assistant", "This is a simulated response.", is_tool=False)
            return

        self.messages.append({"role": "user", "content": user_input})

        max_iterations = 10
        for iteration in range(max_iterations):
            start_time = time.time()
            self.status_indicator.start()
            response = self.model_caller(self.messages, self.tool_schemas if self.tool_schemas else None)
            elapsed = time.time() - start_time
            self.status_indicator.complete()

            usage = response.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            self.status_bar.update_tokens(input_tokens, output_tokens)
            self.status_bar.update_time(elapsed)

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")
            reasoning = response.get("reasoning")

            if reasoning:
                self.show_reasoning(reasoning)

            if tool_calls:
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", "{}")

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

                    tool_start = time.time()
                    result = self.tool_dispatch(tool_name, tool_args)
                    tool_elapsed = time.time() - tool_start

                    self.show_tool_complete(tool_name, action, tool_elapsed)
                    self.show_tool_result_summary(tool_name, result)

                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    })
                continue

            if content:
                self.show_separator()
                self.console.print(content)
                self.console.print()
                self.messages.append({"role": "assistant", "content": content})
            break

    async def _handle_command(self, command: str) -> bool:
        cmd = command.lower().strip()

        if cmd in ("/quit", "/exit", "quit", "exit"):
            self.console.print("\n[yellow]Goodbye![/yellow]")
            self.state.running = False
            return True

        if cmd == "/clear":
            self.clear_conversation()
            self.console.print("[dim]Conversation cleared.[/dim]")
            return True

        if cmd == "/help":
            self.console.print("\n[cyan]Available commands:[/cyan]")
            for c in SLASH_COMMANDS:
                self.console.print(f"  {c}")
            return True

        if cmd == "/status":
            self.console.print(f"\n[cyan]Status:[/cyan]")
            self.console.print(f"  Model: {self.model}")
            self.console.print(f"  Session: {self.session_id}")
            self.console.print(f"  Messages: {len(self.messages)}")
            self.console.print(f"  Tools: {self.tool_count}")
            self.console.print(f"  Skills: {self.skill_count}")
            self.console.print(f"  Input Tokens: {self.status_bar.input_tokens}")
            self.console.print(f"  Output Tokens: {self.status_bar.output_tokens}")
            return True

        return False

    async def process_message(self, message: str) -> None:
        if message.startswith("/"):
            await self._handle_command(message)
            self._print_status_bar()
            return

        self.add_message("user", message)
        await self._run_conversation_loop(message)
        self._print_status_bar()

    # ========================================================================
    # 主循环
    # ========================================================================

    async def run(self) -> None:
        self.state.running = True
        logger.info("TUI 主循环启动")
        self.print_banner()

        try:
            while self.state.running:
                if not self.state.welcomed:
                    self._show_welcome_message()
                    self.state.welcomed = True

                try:
                    user_input = await self.session.prompt_async()
                except EOFError:
                    self.state.running = False
                    break
                except KeyboardInterrupt:
                    continue

                if user_input:
                    await self.process_message(user_input.strip())

        except Exception as e:
            logger.error(f"TUI 主循环异常: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()

    def _show_welcome_message(self) -> None:
        pass

    async def shutdown(self) -> None:
        logger.info("TUI 正在关闭...")
        self.state.running = False
        self.state.save()
        self.event_handler.cleanup()
        logger.info("TUI 已关闭")


def create_tui_v2(
    model_caller,
    tool_dispatch,
    model: str,
    session_id: str,
    tool_count: int = 0,
    skill_count: int = 0,
    tool_schemas: list[dict[str, Any]] | None = None,
    tool_categories: dict[str, list[str]] | None = None,
    skill_categories: dict[str, list[str]] | None = None,
    config: dict[str, Any] | None = None,
) -> TUIApp:
    return TUIApp(
        model_caller=model_caller,
        tool_dispatch=tool_dispatch,
        model=model,
        session_id=session_id,
        tool_count=tool_count,
        skill_count=skill_count,
        tool_schemas=tool_schemas,
        tool_categories=tool_categories,
        skill_categories=skill_categories,
        config=config,
    )
