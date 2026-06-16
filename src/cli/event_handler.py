"""TUIEventHandler - TUI 事件处理系统。

处理用户输入、系统消息和工具调用事件。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from rich.console import Console

from src.cli.state import TUIState
from src.cli.widgets import ActivityFeed, StatusBar
from src.cli.streaming import StreamingStatusIndicator
from src.conversation.events import EventBus, EventType

logger = logging.getLogger(__name__)


class TUIEventHandler:
    def __init__(self, state: TUIState, session_db=None):
        self.state = state
        self.session_db = session_db
        self.pending_clarification: dict[str, Any] | None = None

    async def handle_user_input(self, user_input: str) -> None:
        self.state.input_history.append(user_input)

        if user_input.startswith("/"):
            await self._handle_command(user_input)
            return

        if self.pending_clarification:
            await self._handle_clarification_response(user_input)
            return

        await self._send_message(user_input)

    async def _handle_command(self, command: str) -> None:
        parts = command.split()
        cmd = parts[0].lower()

        commands = {
            "/help": self._cmd_help,
            "/clear": self._cmd_clear,
            "/quit": self._cmd_quit,
            "/resume": self._cmd_resume,
            "/status": self._cmd_status,
            "/tools": self._cmd_tools,
        }

        handler = commands.get(cmd)
        if handler:
            await handler(parts[1:])
        else:
            print(f"未知命令: {cmd}。输入 /help 查看可用命令。")

    async def _cmd_help(self, args: list[str]) -> None:
        print("""
可用命令：
  /help          - 显示此帮助信息
  /clear         - 清空屏幕
  /quit          - 退出 TUI
  /resume [id]   - 恢复会话
  /status        - 显示当前状态
  /tools         - 显示工具调用历史

快捷键：
  Enter          - 发送消息
  Ctrl+D         - 退出
  Ctrl+C         - 中断
  Ctrl+U         - 清空输入
  Shift+Enter    - 换行
""")

    async def _cmd_clear(self, args: list[str]) -> None:
        print("\033[2J\033[H", end="")

    async def _cmd_quit(self, args: list[str]) -> None:
        self.state.running = False

    async def _cmd_resume(self, args: list[str]) -> None:
        if args:
            session_id = args[0]
            self.state.session_id = session_id
            print(f"已恢复到会话 {session_id}")
        else:
            print("用法: /resume <session_id>")

    async def _cmd_status(self, args: list[str]) -> None:
        print(f"会话 ID: {self.state.session_id or '无'}")
        print(f"加载状态: {'加载中...' if self.state.loading else '就绪'}")
        print(f"工具调用次数: {len(self.state.tool_calls)}")
        print(f"输入历史: {len(self.state.input_history)} 条")

    async def _cmd_tools(self, args: list[str]) -> None:
        if not self.state.tool_calls:
            print("暂无工具调用记录。")
            return

        print("\n工具调用历史:")
        for i, tc in enumerate(self.state.tool_calls[-10:], 1):
            status_icon = {"start": "⏳", "running": "🔄", "success": "✅", "error": "❌"}.get(tc.status, "❓")
            print(f"  {i}. {status_icon} {tc.tool_name} ({tc.status})")
            if tc.result:
                print(f"     结果: {tc.result[:100]}...")
        print()

    async def _handle_clarification_response(self, response: str) -> None:
        if self.pending_clarification:
            question_id = self.pending_clarification.get("id")
            logger.info(f"澄清问题 {question_id} 已回复: {response}")
            self.pending_clarification = None

    async def _send_message(self, message: str) -> None:
        self.state.loading = True
        logger.info(f"发送消息: {message[:50]}...")
        print(f"\n🤔 思考中: {message[:80]}...\n")
        await asyncio.sleep(0.5)
        self.state.loading = False
        print("✅ 响应就绪（模拟）\n")

    def handle_interrupt(self) -> None:
        logger.info("用户中断当前操作")
        self.state.loading = False
        print("\n⚠️  已中断操作\n")

    def handle_tool_call_start(self, tool_name: str, args: dict[str, Any]) -> int:
        index = len(self.state.tool_calls)
        self.state.add_tool_call(tool_name, args)
        logger.info(f"工具调用开始: {tool_name}")
        return index

    def handle_tool_call_complete(self, index: int, success: bool, result: str) -> None:
        status = "success" if success else "error"
        self.state.update_tool_call(index, status, result)
        logger.info(f"工具调用完成: {self.state.tool_calls[index].tool_name} ({status})")

    def cleanup(self) -> None:
        self.pending_clarification = None
        logger.info("事件处理器已清理")


class ConversationEventHandler:
    """ConversationLoop 事件处理器，统一管理 TUI 对对话事件的订阅。

    职责：
    1. 模型调用生命周期：启动/停止状态指示器，更新状态栏
    2. 工具执行生命周期：显示工具状态，保存 JSONL
    3. 会话持久化：保存助手回复到 JSONL

    设计理由：
    - 将散落的多处 loop.events.on() 调用集中到单一类
    - 通过 register(events) 一次性注册所有订阅，与 MemoryEventHandler 模式一致
    - 解耦 TUIApp 与事件订阅细节，_run_conversation_loop 只需一行注册代码
    """

    def __init__(
        self,
        console: Console,
        status_bar: StatusBar,
        status_indicator: StreamingStatusIndicator,
        session_id: str = "",
        jsonl_store=None,
        session_db=None,
    ):
        self.console = console
        self.status_bar = status_bar
        self.status_indicator = status_indicator
        self.session_id = session_id
        self.jsonl_store = jsonl_store
        self.session_db = session_db
        self._current_tool_action = "exec"

    def register(self, events: EventBus) -> None:
        """将所有处理器注册到事件总线。"""
        events.on(EventType.MODEL_REQUEST, self._on_model_request)
        events.on(EventType.MODEL_RESPONSE, self._on_model_response)
        events.on(EventType.TOOL_START, self._on_tool_start)
        events.on(EventType.TOOL_END, self._on_tool_end)
        events.on(EventType.MESSAGE_APPEND, self._on_message_append)
        events.on(EventType.DELEGATION_START, self._on_delegation_start)
        events.on(EventType.DELEGATION_COMPLETE, self._on_delegation_complete)
        events.on(EventType.DELEGATION_FAIL, self._on_delegation_fail)

    def _on_model_request(self, data: dict[str, Any]) -> None:
        """模型开始请求：启动状态指示器。"""
        self.status_indicator.start()

    def _on_model_response(self, data: dict[str, Any]) -> None:
        """模型响应完成：停止指示器、更新状态栏。"""
        elapsed = data.get("elapsed", 0)
        response = data["response"]

        self.status_indicator.complete()
        self.status_bar.update_time(elapsed)

        if isinstance(response, dict):
            usage = response.get("usage", {})
            self.status_bar.update_tokens(
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
            )

    def _on_tool_start(self, data: dict[str, Any]) -> None:
        """工具开始执行：显示 UI。"""
        tool_name = data["tool_name"]
        tool_args = data["tool_args"]
        child_tag = self._child_tag(data)

        action = self._extract_tool_action(tool_name, tool_args)
        self._current_tool_action = action

        if child_tag:
            self.console.print(f"  [magenta]{child_tag}[/magenta]")
        self.console.print(ActivityFeed.format_start(tool_name, action))

    def _on_tool_end(self, data: dict[str, Any]) -> None:
        """工具执行结束：显示结果。"""
        tool_name = data["tool_name"]
        result = data["result"]
        elapsed = data["elapsed"]
        child_tag = self._child_tag(data)

        action = self._current_tool_action
        self.console.print(ActivityFeed.format_complete(tool_name, action, elapsed))
        if not child_tag:
            self._show_tool_result_summary(tool_name, result)

    def _on_message_append(self, data: dict[str, Any]) -> None:
        """消息追加到对话历史时，统一持久化到 SQLite 和 JSONL。

        设计理由：
        - 所有消息持久化通过 MESSAGE_APPEND 事件集中处理
        - 与工具执行生命周期（TOOL_START/TOOL_END）完全解耦
        - 支持 assistant（含 tool_calls）、tool、assistant（纯文本）三种消息类型
        """
        if not self.session_id or self.session_id == "new_session":
            return

        message = data["message"]
        role = message.get("role")
        content = message.get("content") or ""

        if role == "assistant" and message.get("tool_calls"):
            # assistant 消息含 tool_calls：JSONL 存完整结构，SQLite 逐个存 tool_call
            tool_calls = message["tool_calls"]
            reasoning = data.get("reasoning")
            usage = data.get("usage")
            if self.jsonl_store:
                try:
                    self.jsonl_store.append_message(
                        self.session_id, role="assistant",
                        content=content, tool_calls=tool_calls,
                        reasoning=reasoning, usage=usage,
                    )
                except Exception as e:
                    logger.debug(f"Failed to save assistant(tool_calls) to JSONL: {e}")
            if self.session_db:
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    tool_args = func.get("arguments", "{}")
                    try:
                        self.session_db.insert_message(
                            self.session_id, role="tool_call",
                            content=tool_args if isinstance(tool_args, str) else json.dumps(tool_args, ensure_ascii=False),
                            tool_name=tool_name, tool_call_id=tc.get("id", ""),
                        )
                        self.session_db.increment_tool_call_count(self.session_id)
                    except Exception as e:
                        logger.debug(f"Failed to save tool_call to SQLite: {e}")

        elif role == "tool":
            # tool 结果消息
            tool_call_id = message.get("tool_call_id", "")
            tool_name = message.get("tool_name", "")
            if self.jsonl_store:
                try:
                    self.jsonl_store.append_message(
                        self.session_id, role="tool",
                        content=content, tool_call_id=tool_call_id,
                        tool_name=tool_name,
                    )
                except Exception as e:
                    logger.debug(f"Failed to save tool message to JSONL: {e}")
            if self.session_db:
                try:
                    self.session_db.insert_message(
                        self.session_id, role="tool_result",
                        content=content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                        tool_name=tool_name, tool_call_id=tool_call_id,
                    )
                except Exception as e:
                    logger.debug(f"Failed to save tool message to SQLite: {e}")

        elif role == "assistant":
            # 纯文本 assistant 消息（最终响应）
            # 设计理由：reasoning 和 usage 从事件数据而非 message dict 中获取
            # 因为 message dict 需要保持 OpenAI API 格式，不含额外字段
            reasoning = data.get("reasoning")
            usage = data.get("usage")
            if self.session_db:
                try:
                    self.session_db.insert_message(self.session_id, "assistant", content)
                except Exception as e:
                    logger.debug(f"Failed to save assistant message to SQLite: {e}")
            if self.jsonl_store:
                try:
                    self.jsonl_store.append_message(
                        self.session_id, role="assistant", content=content,
                        reasoning=reasoning, usage=usage,
                    )
                except Exception as e:
                    logger.debug(f"Failed to save assistant message to JSONL: {e}")

    def _child_tag(self, data: dict[str, Any]) -> str:
        """生成子 Agent 标识符，主 Agent 事件返回空字符串。"""
        child_task_id = data.get("child_task_id", "")
        if child_task_id:
            return f"[子Agent:{child_task_id}]"
        return ""

    def _on_delegation_start(self, data: dict[str, Any]) -> None:
        """子 Agent 委托开始。"""
        task_id = data.get("task_id", "")
        goal = data.get("goal", "")[:60]
        role = data.get("role", "leaf")
        self.console.print(
            f"\n[cyan]{'─' * 50}[/cyan]"
            f"\n[cyan]▶ 子Agent启动[/cyan] [bold]{task_id}[/bold] ({role})"
            f"\n[cyan]  目标: {goal}[/cyan]"
        )

    def _on_delegation_complete(self, data: dict[str, Any]) -> None:
        """子 Agent 委托完成。"""
        task_id = data.get("task_id", "")
        duration = data.get("duration", 0)
        summary = data.get("summary", "")[:100]
        self.console.print(
            f"[green]✓ 子Agent完成[/green] [bold]{task_id}[/bold] ({duration:.1f}s)"
            f"\n[green]  结果: {summary}[/green]"
            f"\n[cyan]{'─' * 50}[/cyan]\n"
        )

    def _on_delegation_fail(self, data: dict[str, Any]) -> None:
        """子 Agent 委托失败。"""
        task_id = data.get("task_id", "")
        error = data.get("error", "")[:100]
        duration = data.get("duration", 0)
        self.console.print(
            f"[red]✗ 子Agent失败[/red] [bold]{task_id}[/bold] ({duration:.1f}s)"
            f"\n[red]  错误: {error}[/red]"
            f"\n[cyan]{'─' * 50}[/cyan]\n"
        )

    def _extract_tool_action(self, tool_name: str, tool_args: str | dict) -> str:
        """提取工具操作的简短描述，用于 UI 展示。"""
        try:
            args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
            if not args_dict:
                return "exec"

            if tool_name == "terminal":
                cmd = args_dict.get("command", "")
                return cmd[:40] if cmd else "exec"
            elif tool_name == "read_file":
                path = args_dict.get("path", "")
                return f"read: {path}" if path else "exec"
            elif tool_name == "write_file":
                path = args_dict.get("path", "")
                return f"write: {path}" if path else "exec"
            elif tool_name == "todo":
                todos = args_dict.get("todos")
                merge = args_dict.get("merge", False)
                if todos:
                    return f"{len(todos)} tasks ({'merge' if merge else 'replace'})"
                return "read todos"
            elif tool_name == "search_files":
                pattern = args_dict.get("pattern", "")
                return f"search: {pattern}" if pattern else "exec"
            elif tool_name == "patch":
                path = args_dict.get("path", "")
                return f"patch: {path}" if path else "exec"
            elif tool_name == "execute_code":
                code = args_dict.get("code", "")
                preview = code[:30].replace("\n", " ")
                return f"code: {preview}..." if code else "exec"
            elif tool_name in ("skill_manage", "memory", "cronjob", "process"):
                action = args_dict.get("action", "")
                return f"{action}" if action else "exec"
            else:
                for v in args_dict.values():
                    if not isinstance(v, (dict, list)):
                        val_str = str(v)
                        return val_str[:30] + "..." if len(val_str) > 30 else val_str
                return "exec"
        except (json.JSONDecodeError, TypeError):
            return "exec"

    def _show_tool_result_summary(self, tool_name: str, result: str) -> None:
        """显示工具结果摘要。"""
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
            elif tool_name == "todo":
                self._show_todo_list(data)
            else:
                self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))
        except (json.JSONDecodeError, AttributeError):
            self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))

    def _show_todo_list(self, data: dict) -> None:
        """以对话框列表格式显示 todo 任务列表。"""
        todos = data.get("todos", [])
        summary = data.get("summary", {})
        total = summary.get("total", 0)
        pending = summary.get("pending", 0)
        in_progress = summary.get("in_progress", 0)
        completed = summary.get("completed", 0)
        cancelled = summary.get("cancelled", 0)

        markers = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
            "cancelled": "[~]",
        }
        colors = {
            "pending": "dim",
            "in_progress": "yellow",
            "completed": "green",
            "cancelled": "red",
        }

        self.console.print()
        self.console.print(f"[bold cyan]📋 Todo List ({total} tasks)[/bold cyan]")
        self.console.print("─" * 40)

        if not todos:
            self.console.print("[dim]  No tasks in the list.[/dim]")
        else:
            for task in todos:
                task_id = task.get("id", "?")
                content = task.get("content", "(no description)")
                status = task.get("status", "pending")

                marker = markers.get(status, "[?]")
                color = colors.get(status, "white")

                if len(content) > 60:
                    content = content[:57] + "..."

                self.console.print(f"  [{color}]{marker}[/{color}] [{color}]{task_id}. {content}[/{color}]")

        self.console.print("─" * 40)
        summary_parts = []
        if pending:
            summary_parts.append(f"[dim]{pending} pending[/dim]")
        if in_progress:
            summary_parts.append(f"[yellow]{in_progress} active[/yellow]")
        if completed:
            summary_parts.append(f"[green]{completed} done[/green]")
        if cancelled:
            summary_parts.append(f"[red]{cancelled} cancelled[/red]")

        if summary_parts:
            self.console.print("  " + " | ".join(summary_parts))
        self.console.print()
