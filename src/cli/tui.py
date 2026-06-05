"""TUI 主模块。

提供完整的 TUI 功能，包括界面渲染、对话循环、命令处理等。
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
from src.cli.widgets import StatusBar, ActivityFeed
from src.conversation.loop import ConversationLoop
from src.conversation.events import EventType

logger = logging.getLogger(__name__)

SLASH_COMMANDS = [
    "/clear", "/status", "/sessions", "/title",
    "/skills", "/skills enable", "/skills disable",
    "/tools", "/compress", "/quit", "/exit",
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
        session_db=None,
        jsonl_store=None,
        memory_manager=None,
        skill_manager=None,
        debug: bool = False,
    ):
        self.config = config or {}
        self.debug = debug
        self.state = TUIState()
        self.event_handler = TUIEventHandler(self.state)
        self.session_db = session_db
        self.jsonl_store = jsonl_store
        self.memory_manager = memory_manager
        self.skill_manager = skill_manager

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
        self._last_reasoning: str = ""
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
        banner_text.append(f"Session: {self.session_id}\n\n", style="dim")

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
        self._save_message_to_storage(role, content)

    def _save_message_to_storage(self, role: str, content: str) -> None:
        """保存消息到 SessionDB 和 JsonlSessionStore。"""
        if not self.session_id or self.session_id == "new_session":
            return

        # 保存到 SQLite（用于搜索和统计）
        if self.session_db:
            try:
                self.session_db.insert_message(self.session_id, role, content)
            except Exception as e:
                logger.debug(f"Failed to save message to SQLite: {e}")

        # 保存到 JSONL（用于完整历史恢复）
        if self.jsonl_store:
            try:
                self.jsonl_store.append_message(self.session_id, role, content)
            except Exception as e:
                logger.debug(f"Failed to save message to JSONL: {e}")

    def show_reasoning(self, reasoning: str, elapsed_ms: float = 0) -> None:
        if not reasoning:
            return
        if elapsed_ms < 1000:
            time_str = f"{elapsed_ms:.0f}ms"
        else:
            time_str = f"{elapsed_ms / 1000:.1f}s"
        self.console.print(f"[bold orange]Thought ({time_str}):[/bold orange]")
        self.console.print(f"[dim]{reasoning}[/dim]")
        self.console.print()

    def show_tool_start(self, tool_name: str, action: str) -> None:
        self.console.print(ActivityFeed.format_start(tool_name, action))

    def show_tool_complete(self, tool_name: str, action: str, elapsed: float) -> None:
        self.console.print(ActivityFeed.format_complete(tool_name, action, elapsed))

    def show_tool_result_summary(self, tool_name: str, result: str) -> None:
        try:
            data = json.loads(result)
            if tool_name == "read_file":
                lines = data.get("content", "").count("\n") + 1
                self.console.print(ActivityFeed.format_result(tool_name, f"read_file: {lines} lines read"))
            elif tool_name == "write_file":
                bytes_written = data.get("bytes_written", 0)
                self.console.print(ActivityFeed.format_result(tool_name, f"write_file: {bytes_written} bytes written"))
            elif tool_name == "search_files":
                count = data.get("total_found", 0)
                self.console.print(ActivityFeed.format_result(tool_name, f"search_files: {count} files found"))
            elif tool_name == "terminal":
                exit_code = data.get("exit_code", -1)
                self.console.print(ActivityFeed.format_result(tool_name, f"terminal: exit code {exit_code}"))
            else:
                self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))
        except (json.JSONDecodeError, AttributeError):
            self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))

    def show_separator(self, agent_name: str = "NanoHermes") -> None:
        self.console.print(f"┌─ {agent_name} " + "─" * 50, style="bold yellow")

    def clear_conversation(self) -> None:
        self.conversation_lines.clear()
        self.messages = [m for m in self.messages if m.get("role") == "system"]
        self._last_reasoning = ""

    def _print_status_bar(self) -> None:
        self.console.print(self.status_bar.render())
        self.console.print()

    # ========================================================================
    # 对话循环
    # ========================================================================

    def _create_model_caller_wrapper(self):
        """创建模型调用包装器，添加状态指示器和计时。"""
        call_start_time = [0]

        def wrapped_caller(messages, tools):
            call_start_time[0] = time.time()
            self.status_indicator.start()
            try:
                response = self.model_caller(messages, tools)
                return response
            finally:
                elapsed = time.time() - call_start_time[0]
                self.status_indicator.complete()

                # 更新状态栏
                if isinstance(response, dict):
                    usage = response.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    self.status_bar.update_tokens(input_tokens, output_tokens)
                    self.status_bar.update_time(elapsed)

        return wrapped_caller

    def _on_tool_start_handler(self, data: dict[str, Any]) -> None:
        """工具开始执行时的事件处理器。"""
        tool_name = data["tool_name"]
        tool_args = data["tool_args"]
        tool_call = data.get("tool_call", {})
        
        try:
            args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
            action = next(iter(args_dict.values())) if args_dict else "exec"
            if isinstance(action, dict):
                action = "exec"
            elif len(str(action)) > 20:
                action = str(action)[:20] + "..."
        except (json.JSONDecodeError, StopIteration, TypeError):
            action = "exec"

        self.show_tool_start(tool_name, action)
        self._current_tool_action = action

        # 保存 tool_call 到 JSONL
        self._save_to_jsonl("tool_call", tool_name=tool_name, tool_args=tool_args,
                           tool_call_id=tool_call.get("id", ""))

    def _on_tool_end_handler(self, data: dict[str, Any]) -> None:
        """工具执行结束时的事件处理器。"""
        tool_name = data["tool_name"]
        result = data["result"]
        elapsed = data["elapsed"]
        tool_call = data.get("tool_call", {})
        
        action = getattr(self, "_current_tool_action", "exec")
        self.show_tool_complete(tool_name, action, elapsed)
        self.show_tool_result_summary(tool_name, result)

        # 保存 tool_result 到 JSONL
        self._save_to_jsonl("tool_result", tool_call_id=tool_call.get("id", ""),
                           tool_name=tool_name, content=result,
                           metadata={"elapsed": elapsed})

    def _on_model_response_handler(self, data: dict[str, Any]) -> None:
        """模型响应完成后的事件处理器，保存助手回复到 JSONL。"""
        response = data["response"]

        if not self.session_id or self.session_id == "new_session":
            return

        # 保存助手回复到 JSONL
        content = response.get("content", "")
        reasoning = response.get("reasoning")
        usage = response.get("usage")
        tool_calls = response.get("tool_calls")

        if self.jsonl_store:
            try:
                self.jsonl_store.append_message(
                    self.session_id,
                    role="assistant",
                    content=content,
                    tool_calls=tool_calls,
                    reasoning=reasoning,
                    usage=usage,
                )
            except Exception as e:
                logger.debug(f"Failed to save assistant message to JSONL: {e}")

    def _save_to_jsonl(self, role: str, **kwargs) -> None:
        """保存消息到 JSONL 的通用方法。"""
        if not self.session_id or self.session_id == "new_session":
            return
        if not self.jsonl_store:
            return
        try:
            self.jsonl_store.append_message(self.session_id, role=role, **kwargs)
        except Exception as e:
            logger.debug(f"Failed to save {role} to JSONL: {e}")

    async def _run_conversation_loop(self, user_input: str) -> None:
        """使用 ConversationLoop 运行对话循环。"""
        if not self.model_caller or not self.tool_dispatch:
            self.add_message("assistant", "This is a simulated response.", is_tool=False)
            return

        self.messages.append({"role": "user", "content": user_input})
        self._save_message_to_storage("user", user_input)

        # 创建 ConversationLoop 实例
        wrapped_model_caller = self._create_model_caller_wrapper()
        loop = ConversationLoop(
            model_call=wrapped_model_caller,
            tool_dispatch=self.tool_dispatch,
            debug=self.debug,
        )
        
        # 订阅事件
        loop.events.on(EventType.TOOL_START, self._on_tool_start_handler)
        loop.events.on(EventType.TOOL_END, self._on_tool_end_handler)
        loop.events.on(EventType.MODEL_RESPONSE, self._on_model_response_handler)

        # 注册 Memory 事件处理器
        memory_handler = None
        if self.memory_manager:
            from src.memory.event_handler import MemoryEventHandler
            memory_handler = MemoryEventHandler(self.memory_manager, self.session_id)
            memory_handler.register(loop.events)

        # 运行对话循环
        result = loop.run(
            messages=self.messages,
            tools=self.tool_schemas if self.tool_schemas else None,
        )

        # 注入记忆上下文到消息历史（如果有预取缓存）
        if memory_handler and memory_handler.prefetch_cache:
            memory_context = memory_handler.prefetch_cache
            # 在用户消息之前插入记忆上下文（作为 system 消息）
            # 找到最后一条用户消息的位置
            for i in range(len(self.messages) - 1, -1, -1):
                if self.messages[i].get("role") == "user":
                    self.messages.insert(i, {
                        "role": "system",
                        "content": memory_context,
                    })
                    break

        # 处理结果
        final_response = result.get("final_response", "")
        reasoning = result.get("reasoning")

        if reasoning:
            self.show_reasoning(reasoning)

        if final_response:
            self.show_separator()
            self.console.print(final_response)
            self.console.print()
            self.messages.append({"role": "assistant", "content": final_response})
            self._save_message_to_storage("assistant", final_response)

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

        if cmd == "/sessions":
            await self._cmd_sessions()
            return True

        if cmd.startswith("/resume"):
            parts = command.strip().split(None, 1)
            identifier = parts[1] if len(parts) > 1 else None
            await self._cmd_resume(identifier)
            return True

        if cmd.startswith("/compress"):
            parts = command.strip().split(None, 1)
            focus_topic = parts[1] if len(parts) > 1 else None
            await self._cmd_compress(focus_topic)
            return True

        if cmd.startswith("/title"):
            parts = command.strip().split(None, 1)
            title = parts[1] if len(parts) > 1 else None
            await self._cmd_title(title)
            return True

        if cmd == "/skills" or cmd.startswith("/skills "):
            await self._cmd_skills(command)
            return True

        if cmd == "/tools":
            await self._cmd_tools()
            return True

        if cmd == "/reasoning":
            await self._cmd_reasoning()
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

        # 如果是新会话，立即创建会话记录
        if self.session_id == "new_session" and self.session_db:
            self.session_id = self.session_db.create_session(title="新会话", model=self.model)
            self.state.session_id = self.session_id
            self.console.print(f"[dim]新会话已创建: {self.session_id}[/dim]\n")

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

    async def _cmd_sessions(self) -> None:
        """处理 /sessions 命令，列出历史会话。"""
        if not self.session_db:
            self.console.print("[yellow]会话数据库不可用[/yellow]")
            return

        sessions = self.session_db.list_sessions(limit=50)
        if not sessions:
            self.console.print("[dim]暂无历史会话[/dim]")
            return

        self.console.print("\n[cyan]历史会话:[/cyan]")
        for s in sessions:
            sid = s.get("session_id", "")
            title = s.get("title") or "(无标题)"
            created = s.get("created_at", "")
            short_id = sid[:8]
            self.console.print(f"  [dim]{created}[/dim]  [bold]{short_id}[/bold]  {title}")
        self.console.print()

    async def _cmd_resume(self, identifier: str | None) -> None:
        """处理 /resume 命令，恢复历史会话。"""
        if not identifier:
            self.console.print("[yellow]用法: /resume <session_id 或 标题关键词>[/yellow]")
            return

        if not self.session_db:
            self.console.print("[yellow]会话数据库不可用[/yellow]")
            return

        # 先尝试按 ID 查找
        session = self.session_db.get_session(identifier)
        if not session:
            # 尝试按标题搜索
            matches = self.session_db.search_sessions_by_title(identifier, limit=5)
            if not matches:
                self.console.print(f"[yellow]未找到匹配的会话: {identifier}[/yellow]")
                return
            if len(matches) == 1:
                session = self.session_db.get_session(matches[0]["id"])
            else:
                self.console.print("[cyan]找到多个匹配，请选择:[/cyan]")
                for m in matches:
                    sid = m.get("id", "")
                    title = m.get("title") or "(无标题)"
                    self.console.print(f"  [bold]{sid[:8]}[/bold]  {title}")
                return

        # 加载会话消息
        messages = self.session_db.get_messages(identifier)
        if not messages:
            self.console.print("[yellow]会话存在但无消息记录[/yellow]")
            return

        # 重新打开会话
        self.session_db.reopen_session(identifier)

        # 更新当前会话 ID 和消息
        old_session_id = self.session_id
        self.session_id = identifier
        self.messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "assistant" and msg.get("tool_calls"):
                try:
                    tool_calls = json.loads(msg.get("tool_calls"))
                    self.messages.append({"role": role, "content": content, "tool_calls": tool_calls})
                except json.JSONDecodeError:
                    self.messages.append({"role": role, "content": content})
            elif role == "tool":
                self.messages.append({"role": role, "content": content, "tool_call_id": msg.get("tool_call_id")})
            else:
                self.messages.append({"role": role, "content": content})

        title = session.get("title") or "(无标题)"
        self.console.print(f"\n[green]已恢复会话: {identifier[:8]} - {title}[/green]")
        self.console.print(f"[dim]共 {len(self.messages)} 条消息[/dim]\n")

    async def _cmd_compress(self, focus_topic: str | None = None) -> None:
        """处理 /compress 命令，手动触发上下文压缩。"""
        if not self.model_caller:
            self.console.print("[yellow]模型调用器不可用[/yellow]")
            return

        if len(self.messages) < 5:
            self.console.print("[yellow]消息太少，无需压缩（至少 5 条）[/yellow]")
            return

        from src.compression import ContextCompressor
        compressor = ContextCompressor(
            model=self.model,
            threshold_percent=0.50,
            protect_first_n=3,
            protect_last_n=20,
            summary_target_ratio=0.20,
        )

        self.console.print("\n[cyan]🗜️ 正在压缩上下文...[/cyan]")

        # 估算当前 token 数
        approx_tokens = sum(len(m.get("content", "") or "") // 4 + 10 for m in self.messages)

        def model_caller(msgs):
            """简单的模型调用适配器。"""
            response = self.model_caller(msgs)
            return response

        try:
            compressed = compressor.compress(
                self.messages,
                current_tokens=approx_tokens,
                focus_topic=focus_topic,
                force=True,
                model_caller=model_caller,
            )

            if len(compressed) == len(self.messages):
                self.console.print("[yellow]压缩未生效（消息数未减少），可能已达最小压缩限度[/yellow]")
                return

            saved = len(self.messages) - len(compressed)
            self.messages = compressed
            self.console.print(f"[green]✓ 压缩完成：{len(self.messages) + saved} -> {len(self.messages)} 条消息（减少 {saved} 条）[/green]")

            # 保存压缩后的消息
            if self.session_db and self.session_id and self.session_id != "new_session":
                for msg in compressed[-min(5, len(compressed)):]:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ("user", "assistant"):
                        self._save_message_to_storage(role, content)

        except Exception as e:
            self.console.print(f"[red]压缩失败: {e}[/red]")
            logger.error(f"Compression failed: {e}", exc_info=True)

    async def _cmd_title(self, title: str | None) -> None:
        """处理 /title 命令，设置会话标题。"""
        if not title:
            self.console.print("[yellow]用法: /title <会话标题>[/yellow]")
            return

        if not self.session_db or self.session_id == "new_session":
            self.console.print("[yellow]会话数据库不可用或未创建会话[/yellow]")
            return

        try:
            self.session_db.set_session_title(self.session_id, title)
            self.console.print(f"[green]会话标题已更新: {title}[/green]")
        except Exception as e:
            self.console.print(f"[red]更新标题失败: {e}[/red]")
            logger.error(f"Failed to update title: {e}", exc_info=True)

    async def _cmd_skills(self, command: str) -> None:
        """处理 /skills 命令，列出或管理技能。"""
        if not self.skill_manager:
            self.console.print("[yellow]技能管理器不可用[/yellow]")
            return

        parts = command.strip().split()

        # /skills - 列出所有技能
        if len(parts) == 1:
            skills = self.skill_manager.list_skills()
            if not skills:
                self.console.print("[dim]暂无已安装的技能[/dim]")
                return

            self.console.print("\n[cyan]已安装的技能:[/cyan]")
            for entry in skills:
                status = "[green]✓[/green]" if entry.enabled else "[dim]✗[/dim]"
                name = entry.skill.name
                desc = entry.skill.description
                uses = f"(使用 {entry.use_count} 次)" if entry.use_count > 0 else ""
                self.console.print(f"  {status} [bold]{name}[/bold] {uses}")
                self.console.print(f"     [dim]{desc}[/dim]")
            self.console.print()
            self.console.print("[dim]用法: /skills enable <name> | /skills disable <name>[/dim]")
            return

        # /skills enable <name> 或 /skills disable <name>
        if len(parts) >= 3:
            action = parts[1].lower()
            skill_name = parts[2]

            if action == "enable":
                success = self.skill_manager.enable_skill(skill_name)
                if success:
                    self.console.print(f"[green]已启用技能: {skill_name}[/green]")
                else:
                    self.console.print(f"[yellow]技能不存在: {skill_name}[/yellow]")
            elif action == "disable":
                success = self.skill_manager.disable_skill(skill_name)
                if success:
                    self.console.print(f"[green]已禁用技能: {skill_name}[/green]")
                else:
                    self.console.print(f"[yellow]技能不存在: {skill_name}[/yellow]")
            else:
                self.console.print(f"[yellow]未知操作: {action}[/yellow]")
                self.console.print("[dim]用法: /skills enable <name> | /skills disable <name>[/dim]")
            return

        self.console.print("[yellow]用法: /skills | /skills enable <name> | /skills disable <name>[/yellow]")

    async def _cmd_tools(self) -> None:
        """处理 /tools 命令，列出所有可用工具。"""
        from src.tools.registry import ToolRegistry

        tools = ToolRegistry.get_all_tools()
        if not tools:
            self.console.print("[dim]暂无已注册的工具[/dim]")
            return

        # 按 toolset 分组
        toolsets: dict[str, list] = {}
        for tool in tools:
            if tool.toolset not in toolsets:
                toolsets[tool.toolset] = []
            toolsets[tool.toolset].append(tool)

        self.console.print("\n[cyan]已注册的工具:[/cyan]")
        for toolset_name, tool_list in sorted(toolsets.items()):
            self.console.print(f"\n  [bold]{toolset_name}:[/bold]")
            for tool in tool_list:
                available = tool.check_fn() if tool.check_fn else True
                status = "[green]✓[/green]" if available else "[dim]✗[/dim]"
                self.console.print(f"    {status} [bold]{tool.name}[/bold] - [dim]{tool.description}[/dim]")
        self.console.print()

    async def shutdown(self) -> None:
        logger.info("TUI 正在关闭...")
        self.state.running = False
        self.state.save()
        self.event_handler.cleanup()
        logger.info("TUI 已关闭")


def create_tui(
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
    session_db=None,
    jsonl_store=None,
    memory_manager=None,
    skill_manager=None,
    debug: bool = False,
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
        session_db=session_db,
        jsonl_store=jsonl_store,
        memory_manager=memory_manager,
        skill_manager=skill_manager,
        debug=debug,
    )
