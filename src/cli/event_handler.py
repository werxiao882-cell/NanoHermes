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
    4. 子 Agent 状态追踪：更新 AgentTaskRegistry（后台委托模式）

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
        task_registry=None,
    ):
        self.console = console
        self.status_bar = status_bar
        self.status_indicator = status_indicator
        self.session_id = session_id
        self.jsonl_store = jsonl_store
        self.session_db = session_db
        self.task_registry = task_registry  # AgentTaskRegistry（可选）
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
        """工具开始执行：显示 UI + 更新子 Agent 进度。

        子 Agent 事件（有 child_task_id）不打印到主输出流，
        只更新 AgentTaskRegistry，通过 bottom_toolbar 实时显示状态。
        用户可通过 /agent <id> 查看完整 transcript。
        """
        child_id = data.get("child_task_id", "")
        tool_name = data["tool_name"]
        tool_args = data["tool_args"]

        action = self._extract_tool_action(tool_name, tool_args)
        self._current_tool_action = action

        if child_id:
            # 子 Agent：只更新 registry，不打印到主输出
            if self.task_registry:
                self.task_registry.update_progress(
                    child_id,
                    last_activity=f"{tool_name}: {action}",
                )
                self.task_registry.append_message(child_id, {
                    "role": "tool",
                    "content": "",
                    "metadata": {"tool_name": tool_name, "status": "start", "action": action},
                })
            return

        # 主 Agent：正常打印
        self.console.print(ActivityFeed.format_start(tool_name, action))

    def _on_tool_end(self, data: dict[str, Any]) -> None:
        """工具执行结束：显示结果 + 更新子 Agent 消息。

        子 Agent 事件不打印到主输出流，只更新 registry。
        """
        child_id = data.get("child_task_id", "")
        tool_name = data["tool_name"]
        result = data["result"]
        elapsed = data["elapsed"]

        action = self._current_tool_action

        if child_id:
            # 子 Agent：只更新 registry
            if self.task_registry:
                task = self.task_registry.get(child_id)
                if task:
                    self.task_registry.update_progress(
                        child_id,
                        tool_calls=task.progress.tool_calls + 1,
                    )
                self.task_registry.append_message(child_id, {
                    "role": "tool",
                    "content": result[:200] if result else "",
                    "metadata": {"tool_name": tool_name, "status": "end", "elapsed": elapsed},
                })
            return

        # 主 Agent：正常打印
        self.console.print(ActivityFeed.format_complete(tool_name, action, elapsed))
        self._show_tool_result_summary(tool_name, result)

    def _on_message_append(self, data: dict[str, Any]) -> None:
        """消息追加到对话历史时，统一持久化到 SQLite 和 JSONL。

        设计理由：
        - 所有消息持久化通过 MESSAGE_APPEND 事件集中处理
        - 与工具执行生命周期（TOOL_START/TOOL_END）完全解耦
        - 支持 assistant（含 tool_calls）、tool、assistant（纯文本）三种消息类型
        - 子 Agent 消息追加到 AgentTask.transcript（增量打印用）
        """
        # 子 Agent 消息：追加到 transcript
        child_id = data.get("child_task_id", "")
        if child_id and self.task_registry:
            message = data.get("message", {})
            role = message.get("role", "")
            content = message.get("content", "")
            if role in ("assistant", "user") and content:
                self.task_registry.append_message(child_id, {
                    "role": role,
                    "content": content,
                })
            return  # 子 Agent 消息不持久化到主会话

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
        """子 Agent 委托开始：注册 AgentTask + 打印通知。"""
        task_id = data.get("child_task_id", "") or data.get("task_id", "")
        goal = data.get("goal", "")[:60]
        role = data.get("role", "leaf")
        name = data.get("name", "") or goal[:30].replace(" ", "-").lower()

        # 注册 AgentTask
        if self.task_registry:
            self.task_registry.register(task_id, name, goal)

        self.console.print(
            f"\n[cyan]{'─' * 50}[/cyan]"
            f"\n[cyan]▶ 子Agent启动[/cyan] [bold]{task_id}[/bold] ({role})"
            f"\n[cyan]  目标: {goal}[/cyan]"
            f"\n[cyan]  /agent {task_id} 查看 transcript[/cyan]"
        )

    def _on_delegation_complete(self, data: dict[str, Any]) -> None:
        """子 Agent 委托完成：更新 AgentTask 状态 + 打印通知。"""
        task_id = data.get("child_task_id", "") or data.get("task_id", "")
        duration = data.get("duration", 0)
        summary = data.get("summary", "")[:100]

        # 更新 AgentTask 状态
        if self.task_registry:
            from src.cli.agent_task import AgentTaskStatus
            self.task_registry.update_status(task_id, AgentTaskStatus.COMPLETED)
            self.task_registry.update_progress(task_id, last_activity=f"completed: {summary[:40]}")
            self.task_registry.append_message(task_id, {
                "role": "system",
                "content": f"任务完成 ({duration:.1f}s): {summary}",
            })

        self.console.print(
            f"[green]✓ 子Agent完成[/green] [bold]{task_id}[/bold] ({duration:.1f}s)"
            f"\n[green]  结果: {summary}[/green]"
            f"\n[cyan]{'─' * 50}[/cyan]\n"
        )

    def _on_delegation_fail(self, data: dict[str, Any]) -> None:
        """子 Agent 委托失败：更新 AgentTask 状态 + 打印通知。"""
        task_id = data.get("child_task_id", "") or data.get("task_id", "")
        error = data.get("error", "")[:100]
        duration = data.get("duration", 0)

        # 更新 AgentTask 状态
        if self.task_registry:
            from src.cli.agent_task import AgentTaskStatus
            self.task_registry.update_status(task_id, AgentTaskStatus.FAILED)
            self.task_registry.update_progress(task_id, last_activity=f"failed: {error[:40]}")
            self.task_registry.append_message(task_id, {
                "role": "system",
                "content": f"任务失败 ({duration:.1f}s): {error}",
            })

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
        """显示工具结果摘要（详细版）。

        每个工具显示关键信息 + 内容预览，让用户无需查看完整结果即可了解概况。
        """
        try:
            data = json.loads(result)

            if tool_name == "read_file":
                self._show_read_file_result(data)
            elif tool_name == "write_file":
                self._show_write_file_result(data)
            elif tool_name == "search_files":
                self._show_search_files_result(data)
            elif tool_name == "terminal":
                self._show_terminal_result(data)
            elif tool_name == "patch":
                self._show_patch_result(data)
            elif tool_name == "todo":
                self._show_todo_list(data)
            elif tool_name == "execute_code":
                self._show_execute_code_result(data)
            elif tool_name == "memory":
                self._show_memory_result(data)
            elif tool_name == "cronjob":
                self._show_cronjob_result(data)
            elif tool_name == "skills_list":
                self._show_skills_list_result(data)
            elif tool_name == "skill_view":
                self._show_skill_view_result(data)
            elif tool_name == "skill_manage":
                self._show_skill_manage_result(data)
            elif tool_name == "process":
                self._show_process_result(data)
            elif tool_name == "session_search":
                self._show_session_search_result(data)
            elif tool_name == "search_tool":
                self._show_search_tools_result(data)
            elif tool_name == "web_search":
                self._show_web_search_result(data)
            elif tool_name == "clarify":
                self._show_clarify_result(data)
            elif tool_name == "delegate_task":
                self._show_delegate_task_result(data)
            else:
                self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))
        except (json.JSONDecodeError, AttributeError):
            self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))

    def _show_read_file_result(self, data: dict) -> None:
        """read_file 结果：路径 + 行数 + 前 3 行预览。"""
        path = data.get("path", "")
        total_lines = data.get("total_lines", 0)
        lines_returned = data.get("lines_returned", 0)
        content = data.get("content", "")

        # 路径和行数
        header = f"📄 {path}" if path else "📄 read_file"
        self.console.print(ActivityFeed.format_result("read_file", f"{header} ({lines_returned}/{total_lines} lines)"))

        # 前 3 行预览
        if content:
            preview_lines = content.split("\n")[:3]
            for line in preview_lines:
                # 去掉行号前缀（如 "    1 | "）
                if " | " in line:
                    line = line.split(" | ", 1)[1]
                if len(line) > 80:
                    line = line[:77] + "..."
                self.console.print(f"    [dim]{line}[/dim]")
            if total_lines > 3:
                self.console.print(f"    [dim]... ({total_lines - 3} more lines)[/dim]")

    def _show_write_file_result(self, data: dict) -> None:
        """write_file 结果：路径 + 字节数。"""
        path = data.get("path", "")
        bytes_written = data.get("bytes_written", 0)
        header = f"📝 {path}" if path else "📝 write_file"
        self.console.print(ActivityFeed.format_result("write_file", f"{header} ({bytes_written} bytes)"))

    def _show_search_files_result(self, data: dict) -> None:
        """search_files 结果：数量 + 前 5 个文件名/匹配预览。"""
        # 文件搜索模式
        files = data.get("files", [])
        if files:
            self.console.print(ActivityFeed.format_result("search_files", f"🔍 {len(files)} files found"))
            for f in files[:5]:
                self.console.print(f"    [dim]📁 {f}[/dim]")
            if len(files) > 5:
                self.console.print(f"    [dim]... and {len(files) - 5} more[/dim]")
            return

        # 内容搜索模式
        matches = data.get("matches", [])
        total = data.get("total_found", len(matches))
        self.console.print(ActivityFeed.format_result("search_files", f"🔍 {total} matches found"))
        for m in matches[:5]:
            file_path = m.get("file", "")
            line_num = m.get("line", "")
            match_text = m.get("match", "")
            if len(match_text) > 60:
                match_text = match_text[:57] + "..."
            self.console.print(f"    [dim]{file_path}:{line_num}  {match_text}[/dim]")
        if len(matches) > 5:
            self.console.print(f"    [dim]... and {len(matches) - 5} more[/dim]")

    def _show_terminal_result(self, data: dict) -> None:
        """terminal 结果：退出码 + 输出预览（前 5 行）。"""
        exit_code = data.get("exit_code", -1)
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")
        timed_out = data.get("timed_out", False)

        # 状态
        if timed_out:
            status = "⏱ timeout"
        elif exit_code == 0:
            status = "✓ exit 0"
        else:
            status = f"✗ exit {exit_code}"

        self.console.print(ActivityFeed.format_result("terminal", f"💻 {status}"))

        # stdout 预览
        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines[:5]:
                if len(line) > 80:
                    line = line[:77] + "..."
                self.console.print(f"    [dim]{line}[/dim]")
            if len(lines) > 5:
                self.console.print(f"    [dim]... ({len(lines) - 5} more lines)[/dim]")

        # stderr 预览（如果有）
        if stderr:
            err_lines = stderr.strip().split("\n")
            for line in err_lines[:3]:
                if len(line) > 80:
                    line = line[:77] + "..."
                self.console.print(f"    [red dim]⚠ {line}[/red dim]")

    def _show_patch_result(self, data: dict) -> None:
        """patch 结果：路径 + 替换信息。"""
        path = data.get("path", "")
        status = data.get("status", "")
        matches = data.get("matches_replaced", 1)
        if status == "success":
            self.console.print(ActivityFeed.format_result("patch", f"🔧 {path} ({matches} replaced)"))
        else:
            error = data.get("error", "unknown error")
            self.console.print(ActivityFeed.format_result("patch", f"🔧 {path} failed: {error}"))

    def _show_execute_code_result(self, data: dict) -> None:
        """execute_code 结果：状态 + stdout 预览。"""
        status = data.get("status", "")
        stdout = data.get("stdout", "")
        stderr = data.get("stderr", "")

        if status == "success":
            self.console.print(ActivityFeed.format_result("execute_code", "▶ code executed successfully"))
        else:
            exit_code = data.get("exit_code", "?")
            self.console.print(ActivityFeed.format_result("execute_code", f"▶ code failed (exit {exit_code})"))

        if stdout:
            lines = stdout.strip().split("\n")
            for line in lines[:5]:
                if len(line) > 80:
                    line = line[:77] + "..."
                self.console.print(f"    [dim]{line}[/dim]")
        if stderr:
            for line in stderr.strip().split("\n")[:2]:
                self.console.print(f"    [red dim]⚠ {line}[/red dim]")

    def _show_memory_result(self, data: dict) -> None:
        """memory 结果：操作类型 + 内容预览。"""
        action = data.get("action", "")
        success = data.get("success", False)

        if action == "view":
            memory_entries = data.get("memory", [])
            user_entries = data.get("user", [])
            self.console.print(ActivityFeed.format_result("memory", f"🧠 memory: {len(memory_entries)} entries, {len(user_entries)} user entries"))
            for entry in memory_entries[:3]:
                if isinstance(entry, str) and entry and not entry.startswith("#"):
                    preview = entry[:60] + "..." if len(entry) > 60 else entry
                    self.console.print(f"    [dim]📝 {preview}[/dim]")
            for entry in user_entries[:2]:
                if isinstance(entry, str) and entry and not entry.startswith("#"):
                    preview = entry[:60] + "..." if len(entry) > 60 else entry
                    self.console.print(f"    [dim]👤 {preview}[/dim]")
        elif success:
            self.console.print(ActivityFeed.format_result("memory", f"🧠 memory {action}: success"))
        else:
            error = data.get("error", "unknown")
            self.console.print(ActivityFeed.format_result("memory", f"🧠 memory {action} failed: {error}"))

    def _show_cronjob_result(self, data: dict) -> None:
        """cronjob 结果：操作 + 任务列表预览。"""
        action = data.get("action", "")
        status = data.get("status", "")

        if action == "list":
            jobs = data.get("jobs", [])
            self.console.print(ActivityFeed.format_result("cronjob", f"⏰ {len(jobs)} cron jobs"))
            for job in jobs[:5]:
                name = job.get("name", job.get("job_id", "?"))
                schedule = job.get("schedule", "?")
                job_status = job.get("status", "?")
                icon = "▶" if job_status == "active" else "⏸"
                self.console.print(f"    [dim]{icon} {name} ({schedule}) [{job_status}][/dim]")
            if len(jobs) > 5:
                self.console.print(f"    [dim]... and {len(jobs) - 5} more[/dim]")
        elif status == "success":
            job_id = data.get("job_id", "")
            self.console.print(ActivityFeed.format_result("cronjob", f"⏰ {action}: {job_id}"))
        else:
            msg = data.get("message", "failed")
            self.console.print(ActivityFeed.format_result("cronjob", f"⏰ {action} failed: {msg}"))

    def _show_skills_list_result(self, data: dict) -> None:
        """skills_list 结果：技能数量 + 前 8 个技能名。"""
        skills = data.get("skills", [])
        count = data.get("count", len(skills))
        self.console.print(ActivityFeed.format_result("skills_list", f"🎯 {count} skills available"))
        for skill in skills[:8]:
            name = skill.get("name", "?")
            desc = skill.get("description", "")
            if len(desc) > 50:
                desc = desc[:47] + "..."
            self.console.print(f"    [dim]• {name}: {desc}[/dim]")
        if len(skills) > 8:
            self.console.print(f"    [dim]... and {len(skills) - 8} more (use skill_view to load)[/dim]")

    def _show_skill_view_result(self, data: dict) -> None:
        """skill_view 结果：技能名 + 内容预览。"""
        success = data.get("success", False)
        if success:
            skill = data.get("skill", {})
            name = skill.get("name", "?")
            desc = skill.get("description", "")
            content = skill.get("content", "")
            lines = content.count("\n") + 1 if content else 0
            self.console.print(ActivityFeed.format_result("skill_view", f"🎯 {name} ({lines} lines)"))
            if desc:
                preview = desc[:70] + "..." if len(desc) > 70 else desc
                self.console.print(f"    [dim]{preview}[/dim]")
        else:
            error = data.get("error", "not found")
            self.console.print(ActivityFeed.format_result("skill_view", f"🎯 skill_view: {error}"))

    def _show_skill_manage_result(self, data: dict) -> None:
        """skill_manage 结果：操作 + 技能名。"""
        success = data.get("success", False)
        if success:
            msg = data.get("message", "success")
            self.console.print(ActivityFeed.format_result("skill_manage", f"🎯 {msg}"))
        else:
            error = data.get("error", "failed")
            self.console.print(ActivityFeed.format_result("skill_manage", f"🎯 {error}"))

    def _show_process_result(self, data: dict) -> None:
        """process 结果：操作 + 进程列表/输出预览。"""
        action = data.get("action", "")

        if action == "list":
            processes = data.get("processes", [])
            self.console.print(ActivityFeed.format_result("process", f"⚙ {len(processes)} processes"))
            for proc in processes[:5]:
                pid = proc.get("process_id", proc.get("session_id", "?"))
                cmd = proc.get("command", "?")
                status = proc.get("status", "?")
                icon = "▶" if status == "running" else "⏸"
                if len(cmd) > 50:
                    cmd = cmd[:47] + "..."
                self.console.print(f"    [dim]{icon} {pid}: {cmd} [{status}][/dim]")
        elif action in ("output", "log"):
            output = data.get("output", "")
            is_running = data.get("is_running", False)
            icon = "▶" if is_running else "⏸"
            self.console.print(ActivityFeed.format_result("process", f"⚙ {icon} process output"))
            if output:
                lines = output.strip().split("\n") if isinstance(output, str) else output
                for line in lines[:8]:
                    if isinstance(line, str):
                        if len(line) > 80:
                            line = line[:77] + "..."
                        self.console.print(f"    [dim]{line}[/dim]")
                if len(lines) > 8:
                    self.console.print(f"    [dim]... ({len(lines) - 8} more lines)[/dim]")
        elif action == "start":
            session_id = data.get("session_id", data.get("process_id", "?"))
            self.console.print(ActivityFeed.format_result("process", f"⚙ started: {session_id}"))
        else:
            status = data.get("status", "")
            msg = data.get("message", "")
            icon = "✓" if status == "success" else "✗"
            self.console.print(ActivityFeed.format_result("process", f"⚙ {icon} {action}: {msg}"))

    def _show_session_search_result(self, data: dict) -> None:
        """session_search 结果：模式 + 结果预览。"""
        mode = data.get("mode", "")
        status = data.get("status", "")

        if mode == "browse":
            results = data.get("results", [])
            self.console.print(ActivityFeed.format_result("session_search", f"🕐 {len(results)} recent sessions"))
            for r in results[:5]:
                title = r.get("title", "Untitled")
                msg_count = r.get("message_count", "?")
                time = r.get("started_at", "")[:16] if r.get("started_at") else ""
                self.console.print(f"    [dim]📋 {title} ({msg_count} msgs) {time}[/dim]")
        elif mode == "discover":
            results = data.get("results", [])
            total = data.get("total_matches", 0)
            self.console.print(ActivityFeed.format_result("session_search", f"🕐 {total} matches in {len(results)} sessions"))
            for r in results[:3]:
                title = r.get("title", "Untitled")
                matches = r.get("matches", [])
                self.console.print(f"    [dim]📋 {title} ({len(matches)} matches)[/dim]")
                for m in matches[:2]:
                    content = m.get("content", "")[:50]
                    self.console.print(f"    [dim]   {content}...[/dim]")
        elif mode == "scroll":
            msgs = data.get("window_messages", [])
            self.console.print(ActivityFeed.format_result("session_search", f"🕐 {len(msgs)} messages in view"))
        else:
            msg = data.get("message", status)
            self.console.print(ActivityFeed.format_result("session_search", f"🕐 {msg}"))

    def _show_search_tools_result(self, data: dict) -> None:
        """search_tools 结果：找到的工具列表。"""
        if isinstance(data, list):
            tools = data
        else:
            tools = data.get("tools", data.get("results", []))
            if not tools and "error" in data:
                self.console.print(ActivityFeed.format_result("search_tools", f"🔎 {data['error']}"))
                return

        if not tools:
            self.console.print(ActivityFeed.format_result("search_tools", "🔎 no tools found"))
            return

        self.console.print(ActivityFeed.format_result("search_tools", f"🔎 {len(tools)} tools found"))
        for t in tools[:5]:
            if isinstance(t, dict):
                name = t.get("name", "?")
                desc = t.get("description", "")
            else:
                name = str(t)
                desc = ""
            if len(desc) > 50:
                desc = desc[:47] + "..."
            self.console.print(f"    [dim]• {name}: {desc}[/dim]")

    def _show_web_search_result(self, data: dict) -> None:
        """web_search 结果：搜索结果预览。"""
        status = data.get("status", "")
        results = data.get("results", [])
        query = data.get("query", "")

        if "error" in data:
            self.console.print(ActivityFeed.format_result("web_search", f"🌐 error: {data['error']}"))
            return

        self.console.print(ActivityFeed.format_result("web_search", f"🌐 {len(results)} results for \"{query[:30]}\""))
        for r in results[:5]:
            title = r.get("title", "?")
            url = r.get("url", r.get("href", ""))
            desc = r.get("description", r.get("body", ""))
            if len(title) > 50:
                title = title[:47] + "..."
            if len(desc) > 60:
                desc = desc[:57] + "..."
            self.console.print(f"    [dim]🔗 {title}[/dim]")
            if url:
                self.console.print(f"    [dim blue]{url}[/dim blue]")
            if desc:
                self.console.print(f"    [dim]{desc}[/dim]")

    def _show_clarify_result(self, data: dict) -> None:
        """clarify 结果：问题 + 选项。"""
        status = data.get("status", "")
        question = data.get("question", "")
        choices = data.get("choices", [])

        if status == "clarification_requested":
            self.console.print(ActivityFeed.format_result("clarify", f"❓ {question[:60]}"))
            for i, choice in enumerate(choices[:4], 1):
                self.console.print(f"    [dim]{i}. {choice}[/dim]")
            if not choices:
                self.console.print(f"    [dim](open-ended question)[/dim]")
        else:
            response = data.get("response", "")
            self.console.print(ActivityFeed.format_result("clarify", f"❓ answered: {response[:50]}"))

    def _show_delegate_task_result(self, data: dict) -> None:
        """delegate_task 结果：委托状态 + 子 Agent 信息。"""
        status = data.get("status", "")

        if status == "dispatched":
            task_ids = data.get("task_ids", [])
            task_id = data.get("task_id", "")
            if task_ids:
                self.console.print(ActivityFeed.format_result("delegate_task", f"🤖 dispatched {len(task_ids)} agents: {', '.join(task_ids)}"))
            elif task_id:
                self.console.print(ActivityFeed.format_result("delegate_task", f"🤖 dispatched agent: {task_id}"))
            msg = data.get("message", "")
            if msg:
                self.console.print(f"    [dim]{msg}[/dim]")
        elif status in ("success", "error"):
            # 单任务结果
            summary = data.get("summary", data.get("message", ""))
            duration = data.get("duration", 0)
            task_id = data.get("task_id", "")
            icon = "✓" if status == "success" else "✗"
            self.console.print(ActivityFeed.format_result("delegate_task", f"🤖 {icon} {task_id} ({duration:.1f}s)"))
            if summary:
                preview = summary[:70] + "..." if len(summary) > 70 else summary
                self.console.print(f"    [dim]{preview}[/dim]")
        elif status == "success" and "results" in data:
            # 批量结果
            results = data.get("results", [])
            count = data.get("count", len(results))
            self.console.print(ActivityFeed.format_result("delegate_task", f"🤖 batch: {count} tasks completed"))
            for r in results[:3]:
                tid = r.get("task_id", "?")
                success = r.get("success", False)
                summary = r.get("summary", "")[:40]
                icon = "✓" if success else "✗"
                self.console.print(f"    [dim]{icon} {tid}: {summary}[/dim]")
        else:
            msg = data.get("message", data.get("error", status))
            self.console.print(ActivityFeed.format_result("delegate_task", f"🤖 {msg}"))

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
