"""TUI 主模块。

提供完整的终端用户界面（TUI）功能，包括界面渲染、对话循环、命令处理等。

设计决策：
- 使用 prompt_toolkit 作为底层 TUI 框架，因为它提供成熟的异步输入处理、
  自动补全、历史记录和快捷键绑定功能，避免从零实现终端交互逻辑。
- 采用依赖注入模式，所有外部依赖（model_caller、tool_dispatch、session_db 等）
  通过构造函数注入，而非内部创建。这样做的原因：
  1. 便于单元测试（可以注入 mock 对象）
  2. 遵循单一职责原则（TUIApp 只负责 UI 和对话协调，不关心依赖如何创建）
  3. 支持运行时灵活配置（不同场景可以注入不同的实现）
- 使用状态管理（TUIState）集中管理应用状态，避免状态散落在多个属性中。
- 采用事件驱动架构订阅 ConversationLoop 的事件，实现 UI 与核心对话逻辑的解耦。
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

# 支持的斜杠命令列表，用于自动补全
SLASH_COMMANDS = [
    "/clear", "/status", "/sessions", "/title",
    "/skills", "/skills enable", "/skills disable",
    "/tools", "/compress", "/quit", "/exit",
]


class TUIApp:
    """TUI 主应用类，整合了应用管理和适配器功能。
    
    设计理由：
    - 此类作为 TUI 的"门面"（Facade），协调多个子系统（布局、渲染、对话、事件等）
    - 不直接实现业务逻辑，而是通过依赖注入的组件协作完成
    - 所有外部依赖通过构造函数注入，遵循依赖倒置原则
    """

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
        """初始化 TUI 应用。
        
        参数说明（依赖注入）：
        - model_caller: 调用 LLM API 的函数，注入而非内部创建以支持不同 API 提供商
        - tool_dispatch: 工具分发器，负责根据工具名调用对应实现
        - session_db: 会话数据库（SQLite），用于会话元数据和搜索
        - jsonl_store: JSONL 存储，用于完整消息历史（支持会话恢复）
        - memory_manager: 记忆管理器，提供长期记忆能力
        - skill_manager: 技能管理器，管理可用技能列表
        - config: 配置字典，控制 UI 行为（如打字速度、面板位置等）
        - debug: 是否开启调试模式，影响日志输出和错误处理
        
        设计理由：
        - 所有参数都有默认值，支持部分初始化（测试场景可以只注入必要依赖）
        - 可选依赖使用 None 作为默认值，在运行时检查可用性而非强制要求
        """
        self.config = config or {}
        self.debug = debug
        
        # 状态管理：集中管理应用状态，避免状态散落在多个属性中
        # 使用独立状态对象的好处：
        # 1. 状态变更可以被监听和记录
        # 2. 便于序列化/反序列化（如保存/恢复状态）
        # 3. 测试时可以单独 mock 状态对象
        self.state = TUIState()
        self.event_handler = TUIEventHandler(self.state)
        
        # 存储层依赖（可选）
        self.session_db = session_db
        self.jsonl_store = jsonl_store
        self.memory_manager = memory_manager
        self.skill_manager = skill_manager

        # 布局配置：从 config 读取，支持运行时自定义
        layout_config = LayoutConfig(
            show_tool_panel=self.config.get("show_tool_panel", True),
            tool_panel_position=self.config.get("tool_panel_position", "right"),
        )
        self.layout_manager = LayoutManager(layout_config)

        # UI 组件初始化
        self.key_bindings = self._create_key_bindings()
        self.style = self._create_style()
        self.completer = ContextAwareCompleter()
        self.history = TUIHistory()
        
        # PromptSession 是 prompt_toolkit 的核心组件，负责：
        # - 用户输入处理（支持多行、自动补全、历史导航）
        # - 快捷键绑定
        # - 样式应用
        self.session = PromptSession(
            key_bindings=self.key_bindings,
            style=self.style,
            completer=self.completer,
            history=self.history,
        )
        self.application: Application | None = None

        # 适配器功能：桥接 TUI 与核心对话系统
        self.model_caller = model_caller
        self.tool_dispatch = tool_dispatch
        self.model = model
        self.session_id = session_id
        self.tool_count = tool_count
        self.skill_count = skill_count
        self.tool_schemas = tool_schemas or []
        self.tool_categories = tool_categories or {}
        self.skill_categories = skill_categories or {}

        # 渲染组件
        self.console = Console()
        self.conversation_lines: list[Text] = []
        self.messages: list[dict[str, Any]] = []
        self._last_reasoning: str = ""
        self._current_loop = None
        self.status_bar = StatusBar(model=model, context_window=1_000_000)
        self.typewriter = TypewriterEffect(speed_ms=self.config.get("typing_speed", 10))
        self.streaming_md = StreamingMarkdown()
        self.status_indicator = StreamingStatusIndicator()

        self.state.session_id = session_id
        logger.info("TUIApp 初始化完成")

    def _create_key_bindings(self) -> KeyBindings:
        """创建快捷键绑定。
        
        工作原理：
        - prompt_toolkit 使用装饰器 @bindings.add() 注册快捷键处理器
        - 装饰器内部维护一个快捷键到回调函数的映射表
        - 当用户按下快捷键时，prompt_toolkit 的事件循环查找映射表并调用对应函数
        - "c-d" 表示 Ctrl+D，"c-c" 表示 Ctrl+C（POSIX 终端标准快捷键）
        
        设计理由：
        - Ctrl+D (EOF)：Unix 标准退出快捷键，设置状态并退出应用
        - Ctrl+C (中断)：Unix 标准中断信号，需要：
          1. 设置状态标志停止主循环
          2. 中断正在运行的对话循环（如果有）
          3. 退出 prompt_toolkit 应用
          注意：这里同时设置 state.running 和调用 loop.interrupt()，
          因为 state.running 控制主循环，而 loop.interrupt() 中断后台线程
        """
        bindings = KeyBindings()

        # Ctrl+D：退出应用（EOF 信号）
        @bindings.add("c-d")
        def _(event):
            """处理 Ctrl+D 退出信号。
            
            参数 event 由 prompt_toolkit 自动传入，包含：
            - event.app：当前 Application 实例，用于调用 exit() 退出
            - event.current_buffer：当前输入缓冲区
            """
            self.state.running = False
            event.app.exit()

        # Ctrl+C：中断当前操作并退出
        @bindings.add("c-c")
        def _(event):
            """处理 Ctrl+C 中断信号。
            
            与 Ctrl+D 的区别：
            - Ctrl+D 是优雅退出（等待当前操作完成）
            - Ctrl+C 是强制中断（立即停止当前操作）
            """
            self.event_handler.handle_interrupt()
            self.state.running = False
            # 如果有正在运行的对话循环，尝试中断
            # 使用 hasattr 检查是为了避免在初始化完成前访问不存在的属性
            if hasattr(self, '_current_loop'):
                self._current_loop.interrupt()
            event.app.exit()

        return bindings

    def _create_style(self) -> Style:
        """创建 Rich 样式定义。
        
        设计理由：
        - 使用十六进制颜色码而非命名颜色，确保跨平台一致性
        - 为不同消息类型定义独立样式，提升可读性：
          - 用户消息：蓝色（#00aaff）
          - 助手消息：白色（#ffffff）
          - 系统消息：灰色（#888888）
          - 工具消息：橙色/绿色/红色（状态区分）
        """
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
        """渲染启动横幅，显示模型信息、工具列表和技能列表。
        
        设计理由：
        - 工具/技能按类别分组展示，避免列表过长
        - 每个类别最多显示 5 个，超出部分用"等 N 个"提示
        - 使用 Rich 的 Text 对象而非纯字符串，支持富文本样式
        """
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
        """保存消息到 SessionDB 和 JsonlSessionStore。
        
        双存储策略的设计理由：
        - SQLite（session_db）：用于会话元数据、搜索、统计分析
          - 优势：支持 SQL 查询、FTS5 全文搜索、会话列表
          - 局限：不适合存储大量结构化数据（如 tool_calls）
        - JSONL（jsonl_store）：用于完整消息历史，支持会话精确恢复
          - 优势：保留完整消息结构（tool_calls、reasoning、usage 等）
          - 局限：不支持复杂查询，只能按会话 ID 读取
        
        边界情况处理：
        - 新会话（session_id == "new_session"）不保存，避免创建无效记录
        - 每个存储操作独立 try-except，一个失败不影响另一个
        - 失败时记录 debug 日志而非 error，因为存储失败不应中断对话
        """
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
        """显示模型的思考过程（reasoning content）。
        
        设计理由：
        - 思考时间 < 1s 显示毫秒，>= 1s 显示秒，提升可读性
        - 使用橙色高亮"Thought"标签，与正常回复区分
        - 思考内容用 dim 样式显示，表明这是辅助信息而非主要回复
        """
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
            elif tool_name == "todo":
                self._show_todo_list(data)
            else:
                self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))
        except (json.JSONDecodeError, AttributeError):
            self.console.print(ActivityFeed.format_result(tool_name, f"{tool_name}: completed"))

    def _show_todo_list(self, data: dict) -> None:
        """以对话框列表格式显示 todo 任务列表。
        
        显示格式：
        📋 Todo List (N tasks)
          [ ] Task A (pending)
          [>] Task B (in_progress)
          [x] Task C (completed)
          [~] Task D (cancelled)
        ────────────────────────
          Summary: 2 pending, 1 active, 1 done, 0 cancelled
        """
        todos = data.get("todos", [])
        summary = data.get("summary", {})
        total = summary.get("total", 0)
        pending = summary.get("pending", 0)
        in_progress = summary.get("in_progress", 0)
        completed = summary.get("completed", 0)
        cancelled = summary.get("cancelled", 0)

        # 状态标记映射
        markers = {
            "pending": "[ ]",
            "in_progress": "[>]",
            "completed": "[x]",
            "cancelled": "[~]",
        }
        # 状态颜色映射
        colors = {
            "pending": "dim",
            "in_progress": "yellow",
            "completed": "green",
            "cancelled": "red",
        }

        # 打印标题
        self.console.print()
        self.console.print(f"[bold cyan]📋 Todo List ({total} tasks)[/bold cyan]")
        self.console.print("─" * 40)

        # 打印每个任务
        if not todos:
            self.console.print("[dim]  No tasks in the list.[/dim]")
        else:
            for task in todos:
                task_id = task.get("id", "?")
                content = task.get("content", "(no description)")
                status = task.get("status", "pending")
                
                marker = markers.get(status, "[?]")
                color = colors.get(status, "white")
                
                # 截断过长内容
                if len(content) > 60:
                    content = content[:57] + "..."
                
                self.console.print(f"  [{color}]{marker}[/{color}] [{color}]{task_id}. {content}[/{color}]")

        # 打印摘要
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
        """创建模型调用包装器，添加状态指示器和计时。
        
        闭包设计理由：
        - 使用闭包（而非类）的原因：
          1. 轻量级：只需包装一个函数，无需定义完整类
          2. 状态隔离：call_start_time 通过列表 [0] 存储，避免全局变量
          3. 词法作用域：内部函数可以访问外部函数的 self，无需额外传参
        
        为什么用列表 [0] 而非普通变量：
        - Python 的闭包只能捕获可变对象的引用，不能重新绑定变量名
        - 如果用 call_start_time = 0，内部函数无法修改它（会创建新局部变量）
        - 用列表 [0] 可以通过修改列表内容实现"可变捕获"
        
        状态管理：
        - 调用前：启动状态指示器（旋转动画），记录开始时间
        - 调用后：无论成功/失败（finally），停止指示器并更新状态栏
        - 状态栏更新包括：token 使用量、响应时间，用于性能监控
        """
        call_start_time = [0]  # 使用列表实现闭包可变状态

        def wrapped_caller(messages, tools):
            """包装后的模型调用函数。
            
            签名与原始 model_caller 一致，但添加了：
            - 状态指示器（UI 反馈）
            - 计时（性能监控）
            - token 使用量统计（状态栏更新）
            """
            call_start_time[0] = time.time()
            self.status_indicator.start()
            try:
                response = self.model_caller(messages, tools)
                return response
            finally:
                # finally 确保即使异常也会停止指示器
                elapsed = time.time() - call_start_time[0]
                self.status_indicator.complete()

                # 更新状态栏（仅当响应包含 usage 信息时）
                if isinstance(response, dict):
                    usage = response.get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                    output_tokens = usage.get("output_tokens", 0)
                    self.status_bar.update_tokens(input_tokens, output_tokens)
                    self.status_bar.update_time(elapsed)

        return wrapped_caller

    def _on_tool_start_handler(self, data: dict[str, Any]) -> None:
        """工具开始执行时的事件处理器。
        
        事件驱动架构的设计理由：
        - ConversationLoop 通过 EventBus 发布事件，TUI 订阅感兴趣的事件
        - 优势：解耦核心对话逻辑与 UI 渲染，两者可以独立演化
        - 事件类型：TOOL_START、TOOL_END、MODEL_RESPONSE 等
        
        数据处理：
        - 提取工具名称和参数，生成简短动作描述（如 "read: main.py"）
        - 保存 tool_call 到 JSONL，用于会话恢复时重建完整上下文
        """
        tool_name = data["tool_name"]
        tool_args = data["tool_args"]
        tool_call = data.get("tool_call", {})
        
        action = self._extract_tool_action(tool_name, tool_args)

        self.show_tool_start(tool_name, action)
        self._current_tool_action = action

        # 保存 tool_call 到 JSONL
        self._save_to_jsonl("tool_call", tool_name=tool_name, tool_args=tool_args,
                           tool_call_id=tool_call.get("id", ""))

    def _extract_tool_action(self, tool_name: str, tool_args: str | dict) -> str:
        """提取工具操作的简短描述，用于 UI 展示。
        
        设计理由：
        - 不同工具的关键参数不同，需要针对性提取：
          - terminal：显示命令（截断到 40 字符）
          - read_file/write_file：显示文件路径
          - search_files：显示搜索模式
          - todo：显示任务数量和模式（merge/replace）
        - 通用策略：取第一个非字典/列表的值（简单启发式）
        - 失败时返回 "exec"，确保 UI 不会崩溃
        """
        try:
            args_dict = json.loads(tool_args) if isinstance(tool_args, str) else tool_args
            if not args_dict:
                return "exec"
            
            # 针对常用工具提取有意义的描述
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
                # 通用：取第一个非字典/列表的值
                for v in args_dict.values():
                    if not isinstance(v, (dict, list)):
                        val_str = str(v)
                        return val_str[:30] + "..." if len(val_str) > 30 else val_str
                return "exec"
        except (json.JSONDecodeError, TypeError):
            return "exec"

    def _on_tool_end_handler(self, data: dict[str, Any]) -> None:
        """工具执行结束时的事件处理器。
        
        职责：
        1. 显示工具完成信息（名称、动作、耗时）
        2. 显示结果摘要（根据工具类型解析不同字段）
        3. 保存 tool_result 到 JSONL，用于会话恢复
        
        状态传递：
        - 使用 _current_tool_action 属性在 TOOL_START 和 TOOL_END 之间传递动作描述
        - 这是简单的状态共享方式，避免在事件中重复计算动作描述
        """
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
        """模型响应完成后的事件处理器，保存助手回复到 JSONL。
        
        设计理由：
        - 只在事件处理器中保存，而非在 _run_conversation_loop 末尾保存
        - 原因：ConversationLoop 可能有多轮工具调用，每轮模型响应都需要保存
        - 保存完整结构：content、reasoning、usage、tool_calls
        """
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
        """使用 ConversationLoop 运行对话循环。
        
        异步编程（async/await）的使用理由：
        1. TUI 主循环是异步的（run() 方法是 async），需要 await 子协程
        2. 虽然 ConversationLoop.run() 本身是同步的（阻塞式 API 调用），
           但我们在后台线程中运行它，并用 asyncio.sleep() 轮询完成状态
        3. 异步架构允许 TUI 在等待 API 响应时保持响应（处理 Ctrl+C 等）
        
        线程模型设计：
        - ConversationLoop.run() 在后台线程（ThreadPoolExecutor）中运行
        - 原因：LLM API 调用是阻塞的（同步 HTTP 请求），会阻塞事件循环
        - 主线程通过检查 state.running 标志来检测用户中断（Ctrl+C）
        - 使用 asyncio.sleep(0.1) 轮询，避免忙等待（busy-wait）消耗 CPU
        
        事件订阅机制：
        - 通过 loop.events.on() 订阅 ConversationLoop 的内部事件
        - 事件类型：TOOL_START、TOOL_END、MODEL_RESPONSE
        - 优势：无需修改 ConversationLoop 代码，即可插入 UI 更新逻辑
        - 这是观察者模式的实现，实现核心逻辑与 UI 的解耦
        
        Memory 集成：
        - 如果 memory_manager 可用，创建 MemoryEventHandler 并注册到事件总线
        - MemoryEventHandler 会监听对话事件，自动触发记忆检索和刷写
        - prefetch_cache 包含预取的记忆上下文，需要注入到消息历史中
        """
        if not self.model_caller or not self.tool_dispatch:
            self.add_message("assistant", "This is a simulated response.", is_tool=False)
            return

        self.messages.append({"role": "user", "content": user_input})
        self._save_message_to_storage("user", user_input)

        # 创建 ConversationLoop 实例
        # 包装 model_caller 以添加状态指示器和计时
        wrapped_model_caller = self._create_model_caller_wrapper()
        self._current_loop = ConversationLoop(
            model_call=wrapped_model_caller,
            tool_dispatch=self.tool_dispatch,
            debug=self.debug,
        )
        loop = self._current_loop
        
        # 订阅事件：将 UI 更新逻辑绑定到对话循环的内部事件
        # 这是事件驱动架构的核心：UI 不主动查询，而是被动响应事件
        loop.events.on(EventType.TOOL_START, self._on_tool_start_handler)
        loop.events.on(EventType.TOOL_END, self._on_tool_end_handler)
        loop.events.on(EventType.MODEL_RESPONSE, self._on_model_response_handler)

        # 注册 Memory 事件处理器
        # MemoryEventHandler 会自动监听对话事件，触发记忆相关操作
        memory_handler = None
        if self.memory_manager:
            from src.memory.event_handler import MemoryEventHandler
            memory_handler = MemoryEventHandler(self.memory_manager, self.session_id)
            memory_handler.register(loop.events)

        # 在后台线程运行对话循环，支持 Ctrl+C 中断
        # 使用列表 [None] 而非普通变量，因为需要在嵌套函数中修改
        result = [None]
        exception = [None]

        def _run_loop():
            """在线程池中执行的包装函数。
            
            捕获所有异常并存储到 exception[0]，避免线程异常导致主线程崩溃。
            """
            try:
                result[0] = loop.run(
                    messages=self.messages,
                    tools=self.tool_schemas if self.tool_schemas else None,
                )
            except Exception as e:
                exception[0] = e

        # 使用 ThreadPoolExecutor 在后台线程运行阻塞的对话循环
        # max_workers=1 确保同时只有一个对话在进行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_loop)
            try:
                # 轮询循环：检查是否完成或被中断
                while not future.done():
                    # 检查中断标志（由 Ctrl+C 处理器设置）
                    if not self.state.running:
                        loop.interrupt()
                        break
                    # 异步睡眠 100ms，避免忙等待
                    # 选择 100ms 是平衡响应速度和 CPU 使用率
                    await asyncio.sleep(0.1)
                # 等待线程完成（最多 1 秒）
                future.result(timeout=1)
            except concurrent.futures.TimeoutError:
                # 超时则强制中断对话循环
                loop.interrupt()

        # 如果线程中发生异常，重新抛出到主线程
        if exception[0]:
            raise exception[0]
        if not result[0]:
            return

        # 注入记忆上下文到消息历史（如果有预取缓存）
        # 设计理由：记忆上下文需要在用户消息之前插入，作为 system 消息
        # 这样模型可以在回复时参考记忆内容
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
        final_response = result[0].get("final_response", "")
        reasoning = result[0].get("reasoning")

        if reasoning:
            self.show_reasoning(reasoning)

        if final_response:
            self.show_separator()
            self.console.print(final_response)
            self.console.print()
            self.messages.append({"role": "assistant", "content": final_response})
            self._save_message_to_storage("assistant", final_response)

        # 自动压缩检查（任务 12.21）
        await self._check_auto_compress(result)

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
        """TUI 主循环入口。
        
        异步编程模型：
        - 此方法是 async，因为需要 await prompt_async() 获取用户输入
        - prompt_toolkit 的 prompt_async() 是异步的，不会阻塞事件循环
        - 这使得 TUI 可以在等待用户输入时处理其他异步任务（如后台刷新）
        
        主循环流程：
        1. 初始化：创建会话（如果是新会话）、打印横幅
        2. 循环：等待用户输入 -> 处理命令/消息 -> 显示回复
        3. 退出：捕获异常、执行 shutdown 清理资源
        
        状态管理：
        - state.running 控制循环继续/退出
        - state.welcomed 确保欢迎消息只显示一次
        - session_id 在运行时可能变化（如 /resume 命令）
        
        异常处理：
        - EOFError：用户按下 Ctrl+D（EOF 信号），优雅退出
        - KeyboardInterrupt：用户按下 Ctrl+C，继续循环（不退出）
        - 其他异常：记录日志并重新抛出，由上层处理
        - finally 块确保无论何种退出方式都执行 shutdown
        """
        self.state.running = True
        logger.info("TUI 主循环启动")

        # 如果是新会话，立即创建会话记录
        # 设计理由：在首次用户输入前创建会话，确保 session_id 有效
        if self.session_id == "new_session" and self.session_db:
            self.session_id = self.session_db.create_session(title="新会话", model=self.model)
            self.state.session_id = self.session_id
            self.console.print(f"[dim]新会话已创建: {self.session_id}[/dim]\n")

        self.print_banner()

        try:
            # 主循环：持续运行直到 state.running 被设置为 False
            while self.state.running:
                # 显示欢迎消息（仅一次）
                if not self.state.welcomed:
                    self._show_welcome_message()
                    self.state.welcomed = True

                try:
                    # 异步等待用户输入
                    # prompt_async() 是异步的，不会阻塞事件循环
                    # 这使得 TUI 可以在等待输入时处理其他任务
                    user_input = await self.session.prompt_async()
                except EOFError:
                    # Ctrl+D 触发 EOFError，优雅退出
                    self.state.running = False
                    break
                except KeyboardInterrupt:
                    # Ctrl+C 触发 KeyboardInterrupt，继续循环（不退出）
                    # 用户可以重新输入，而非强制退出应用
                    continue

                # 处理非空输入
                if user_input:
                    await self.process_message(user_input.strip())

        except Exception as e:
            # 记录完整异常堆栈，便于调试
            logger.error(f"TUI 主循环异常: {e}", exc_info=True)
            raise
        finally:
            # 无论何种方式退出，都执行清理
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
        """处理 /resume 命令，恢复历史会话。
        
        恢复流程：
        1. 按 ID 精确查找，或按标题关键词模糊搜索
        2. 如果多个匹配，列出供用户选择
        3. 加载会话消息，重建 messages 列表
        4. 处理 tool_calls 的 JSON 反序列化（存储在 SQLite 中是 JSON 字符串）
        
        边界情况：
        - 标识符为空：提示用法
        - 数据库不可用：提示错误
        - 会话无消息：提示但允许继续（可能是空会话）
        - tool_calls JSON 解析失败：降级为普通消息（不丢失内容）
        """
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

    async def _check_auto_compress(self, response: dict) -> None:
        """自动压缩检查。

        在每次模型响应后检查是否需要自动触发压缩。
        检查条件：
        1. 上下文使用量超过阈值
        2. API 返回 context_length_exceeded 错误
        3. 消息数过多（启发式检查）

        如果满足条件，自动执行压缩。
        """
        if not self.model_caller:
            return

        if len(self.messages) < 10:
            return

        from src.compression import ContextCompressor

        compressor = ContextCompressor(
            model=self.model,
            threshold_percent=0.50,
            protect_first_n=3,
            protect_last_n=20,
            summary_target_ratio=0.20,
        )

        # 检查 1：响应后检查（token 使用量）
        needs_compress = compressor.check_post_response(response)

        # 检查 2：预飞行检查（消息估算）
        if not needs_compress:
            needs_compress = compressor.check_preflight(self.messages)

        # 检查 3：消息数启发式（超过 100 条消息自动触发）
        if not needs_compress and len(self.messages) > 100:
            needs_compress = True

        if needs_compress:
            self.console.print("\\n[yellow]⚡ 上下文接近限制，自动触发压缩...[/yellow]")
            await self._cmd_compress()

    async def _cmd_compress(self, focus_topic: str | None = None) -> None:
        """处理 /compress 命令，手动触发上下文压缩。
        
        压缩策略：
        - threshold_percent=0.50：当消息数超过阈值的 50% 时触发压缩
        - protect_first_n=3：保护前 3 条消息（通常是 system prompt）
        - protect_last_n=20：保护最近 20 条消息（保持上下文连贯性）
        - summary_target_ratio=0.20：摘要目标长度为原文的 20%
        
        设计理由：
        - 使用局部函数 model_caller() 适配接口：
          ContextCompressor 期望的签名是 model_caller(msgs)，
          而 self.model_caller 的签名是 model_caller(messages, tools)
          局部函数桥接了这个差异
        - force=True：用户手动触发时强制执行，忽略自动压缩的阈值检查
        """
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
            result = compressor.compress(
                self.messages,
                current_tokens=approx_tokens,
                focus_topic=focus_topic,
                force=True,
                model_caller=model_caller,
            )

            # compress 返回 dict: {"messages": [...], "summary": "...", ...}
            compressed = result.get("messages", result) if isinstance(result, dict) else result

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
    """工厂函数：创建 TUIApp 实例。
    
    设计理由：
    - 工厂函数而非直接构造的原因：
      1. 简化调用：main.py 可以通过 **config 字典一次性传入所有参数
      2. 参数验证：未来可以在工厂中添加参数验证逻辑
      3. 依赖注入容器：可以作为 DI 容器的注册点
    - 参数与 TUIApp.__init__ 完全一致，只是转发调用
    """
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
