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
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.cli.state import TUIState
from src.cli.event_handler import TUIEventHandler, ConversationEventHandler
from src.cli.layout import LayoutManager, LayoutConfig
from src.cli.completers import ContextAwareCompleter
from src.cli.history import TUIHistory
from src.cli.streaming import TypewriterEffect, StreamingMarkdown, StreamingStatusIndicator
from src.cli.widgets import StatusBar
from src.conversation.loop import ConversationLoop

logger = logging.getLogger(__name__)

# 支持的斜杠命令列表，用于自动补全
SLASH_COMMANDS = [
    "/clear", "/status", "/sessions", "/title",
    "/skills", "/skills enable", "/skills disable",
    "/tools", "/compress", "/quit", "/exit",
]

# 哨兵对象：区分 __init__ 中 session_db 参数"未传" vs "显式传 None"
_UNSET = object()


class TUIApp:
    """TUI 主应用类，整合了应用管理和适配器功能。
    
    设计理由：
    - 此类作为 TUI 的"门面"（Facade），协调多个子系统（布局、渲染、对话、事件等）
    - 不直接实现业务逻辑，而是通过依赖注入的组件协作完成
    - 所有外部依赖通过构造函数注入，遵循依赖倒置原则
    """

    def __init__(
        self,
        *,
        debug: bool = False,
        resume: str | None = None,
        resume_title: str | None = None,
        config: dict[str, Any] | None = None,
        session_db=_UNSET,
        jsonl_store=_UNSET,
        memory_manager=_UNSET,
        skill_manager=_UNSET,
    ):
        """初始化 TUI 应用。

        设计理由：
        - 生产环境：无需传参，内部自动初始化所有依赖（配置/Provider/工具/存储/记忆/提示词）
        - 测试环境：传 session_db（含 None）跳过自动初始化，使用轻量默认值
        - session_db 使用 _UNSET 哨兵区分"未传参"（自动初始化）和"显式传 None"（无数据库）

        Args:
            debug: 是否开启调试模式。
            resume: 恢复会话 ID。
            resume_title: 通过标题恢复会话。
            config: UI 配置覆盖（typing_speed, show_tool_panel 等）。
            session_db: 会话数据库。_UNSET=自动初始化，None=无数据库，实例=使用注入的数据库。
            jsonl_store: JSONL 存储。_UNSET=自动初始化，None=无存储，实例=使用注入的存储。
            memory_manager: 记忆管理器。_UNSET=自动初始化，None=无记忆，实例=使用注入的管理器。
            skill_manager: 技能管理器。_UNSET=自动初始化，None=无技能，实例=使用注入的管理器。
        """
        # ── 1. 参数保存 ──
        # 将构造参数保存为实例属性，供后续初始化阶段和运行时使用
        self.debug = debug
        self._resume = resume
        self._resume_title = resume_title
        self.config = config or {}
        self._injected_session_db = session_db
        self._injected_jsonl_store = jsonl_store
        self._injected_memory_manager = memory_manager
        self._injected_skill_manager = skill_manager

        # ── 2. 日志配置 ──
        # 使用局部导入 logging，避免与模块级 logger 冲突
        # 默认 WARNING 级别减少噪音；debug 模式下 src 命名空间降为 DEBUG
        # 时间格式用 HH:MM:SS（省略日期），因为 TUI 会话通常不超过一天
        from pathlib import Path
        import logging as _logging
        _logging.basicConfig(
            level=_logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        if self.debug:
            _logging.getLogger("src").setLevel(_logging.DEBUG)

        # ── 3. 状态管理 ──
        # TUIState 集中管理应用状态（running/welcomed/session_id 等）
        # TUIEventHandler 处理状态变更的副作用（如中断信号的状态同步）
        self.state = TUIState()
        self.event_handler = TUIEventHandler(self.state)

        # ── 4. 布局管理 ──
        # LayoutManager 负责 TUI 区域划分（对话区、工具面板、状态栏）
        # 布局参数从 config 读取，支持运行时覆盖默认值
        layout_config = LayoutConfig(
            show_tool_panel=self.config.get("show_tool_panel", True),
            tool_panel_position=self.config.get("tool_panel_position", "right"),
        )
        self.layout_manager = LayoutManager(layout_config)

        # ── 5. 输入组件 ──
        # 组装 prompt_toolkit 的输入管线：快捷键 → 样式 → 补全器 → 历史记录 → PromptSession
        # PromptSession 是 prompt_toolkit 的核心，封装了终端输入的所有交互逻辑
        # application 延迟赋值，因为需要在 run() 中根据运行时状态决定是否创建
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

        # ── 6. 渲染组件 ──
        # Console: Rich 渲染入口，所有终端输出通过它完成
        # conversation_lines: 预渲染的 Text 列表，用于对话面板展示
        # messages: 原始消息字典列表，用于发送给 LLM API
        # typewriter/streaming_md/status_indicator: 流式输出的三个层次
        #   - typewriter: 逐字打字效果（视觉体验）
        #   - streaming_md: 流式 Markdown 渲染（内容格式化）
        #   - status_indicator: 流式状态指示器（加载中/就绪）
        # 注意：system_prompt 在步骤 13 组装，此处先初始化为空字符串
        # 步骤 13 完成后会用实际内容替换，并追加到 messages 中
        self.system_prompt = ""
        self.console = Console()
        self.conversation_lines: list[Text] = []
        self.messages: list[dict[str, Any]] = []
        self._last_reasoning: str = ""
        self._current_loop = None
        self.status_bar = None  # 延迟初始化，等 self.model 赋值后创建（见步骤 7）
        self.typewriter = TypewriterEffect(speed_ms=self.config.get("typing_speed", 10))
        self.streaming_md = StreamingMarkdown()
        self.status_indicator = StreamingStatusIndicator()

        # ── 7. 配置加载与 API 凭证 ──
        # 初始化链：配置 → 凭证 → 模型名称
        # API Key 缺失时直接 sys.exit(1)，因为没有凭证无法进行任何 LLM 调用
        # 使用 print 而非 logger，因为此时日志系统刚配置，且这是面向用户的致命错误
        from src.config import load_config, get_api_key, get_base_url
        app_config = load_config()
        api_key = get_api_key(app_config)
        base_url = get_base_url(app_config)
        self.model = app_config.model.name
        self.status_bar = StatusBar(model=self.model, context_window=1_000_000)  # 延迟创建
        if not api_key:
            import sys
            print("[错误] 未设置 API Key，请检查 .env 或配置文件")
            sys.exit(1)

        # ── 8. LLM Provider 客户端 ──
        # 构建调用链：OpenAI SDK 客户端 → ProviderOpenAIClient 封装 → model_caller 可调用对象
        # ProviderOpenAIClient 封装了重试、错误分类、debug 日志等横切关注点
        # build_caller() 返回一个可调用对象，屏蔽了 SDK 细节，供 ConversationLoop 使用
        from openai import OpenAI
        from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
        client = OpenAI(api_key=api_key, base_url=base_url)
        provider_client = ProviderOpenAIClient(client, self.model, debug=self.debug)
        self.model_caller = provider_client.build_caller()

        # ── 9. 工具系统 ──
        # init_all_tools() 触发所有工具模块的加载，每个模块在导入时自动注册
        # exclude_deferred=True 只获取非延迟工具（6 个核心工具），延迟工具通过 search_tools 按需发现
        # tool_categories_info 用于启动横幅按类别展示工具列表
        from src.tools.core.registry import ToolRegistry, get_tool_schemas
        from src.tools.core.dispatcher import dispatch as tool_dispatch_func
        ToolRegistry.init_all_tools()
        self.tool_dispatch = tool_dispatch_func
        self.tool_schemas = get_tool_schemas(exclude_deferred=True)
        self.tool_categories_info = ToolRegistry.get_tool_categories_with_info()

        # ── 10. 技能系统 ──
        # SkillManager 加载 SKILL.md 文件并管理技能的启用/禁用状态
        # skill_categories 按类别分组，用于启动横幅展示和系统提示注入
        from src.skills.manager import SkillManager
        if self._injected_skill_manager is not _UNSET:
            self.skill_manager = self._injected_skill_manager
        else:
            self.skill_manager = SkillManager()
        self.skill_categories = self.skill_manager.get_skills_by_category()

        # ── 11. 会话存储（双存储） ──
        # SessionDB (SQLite): 会话元数据 + FTS5 全文搜索 + 统计分析
        # JsonlSessionStore: 完整消息历史（保留 tool_calls 等结构化字段）
        # session_id 初始为 "new_session"，在 run() 中首次用户输入前创建实际记录
        from src.session.session_db import SessionDB
        from src.session.jsonl_store import JsonlSessionStore
        if self._injected_session_db is not _UNSET:
            self.session_db = self._injected_session_db
        else:
            db_path = Path.home() / ".nanohermes" / "sessions.db"
            self.session_db = SessionDB(db_path)
        if self._injected_jsonl_store is not _UNSET:
            self.jsonl_store = self._injected_jsonl_store
        else:
            self.jsonl_store = JsonlSessionStore()
        self.session_id = "new_session"

        # ── 12. 记忆系统 ──
        # MemoryManager 支持多提供者架构（当前只注册 FileMemoryProvider）
        # FileMemoryProvider 读写 ~/.nanohermes/ 下的 MEMORY.md 和 USER.md
        # 记忆在对话中通过 MemoryEventHandler 自动检索和刷写
        from src.memory import MemoryManager, FileMemoryProvider
        if self._injected_memory_manager is not _UNSET:
            self.memory_manager = self._injected_memory_manager
        else:
            self.memory_manager = MemoryManager()
            hermes_home = str(Path.home() / ".nanohermes")
            file_provider = FileMemoryProvider(hermes_home)
            self.memory_manager.add_provider(file_provider)

        from src.conversation.assembler import PromptAssembler
        assembler = PromptAssembler(
            tool_registry=ToolRegistry,
            skill_manager=self.skill_manager,
        )
        system_prompt_result = assembler.build_system_prompt(
            model=self.model,
            include_memory=True,
            include_user_profile=True,
        )
        self.system_prompt = system_prompt_result.full_text
        # 系统提示组装完成，追加到消息列表开头（步骤 6 时 system_prompt 尚为空）
        if self.system_prompt:
            self.messages.insert(0, {"role": "system", "content": self.system_prompt})

        # ── 14. 初始化完成 ──
        # 同步 session_id 到状态管理器，供事件处理器和 UI 组件使用
        self.state.session_id = self.session_id
        logger.info("TUIApp 初始化完成")

    @property
    def tool_count(self) -> int:
        """动态计算工具数量，避免冗余参数。"""
        return len(self.tool_schemas)

    @property
    def skill_count(self) -> int:
        """动态计算技能数量，避免冗余参数。"""
        return sum(len(skills) for skills in self.skill_categories.values())

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
            if getattr(self, '_current_loop', None) is not None:
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
        - 工具按类别分组展示，每个工具显示名称、描述和加载状态
        - 延迟加载工具用黄色 (deferred) 标记，始终加载工具用绿色 (loaded) 标记
        - 每个类别最多显示 5 个工具，超出部分用"等 N 个"提示
        - 使用 Rich 的 Text 对象而非纯字符串，支持富文本样式
        """
        banner_text = Text()
        banner_text.append("NANOHERMES AGENT", style="bold yellow")
        banner_text.append("\n\n")
        banner_text.append(f"Model: {self.model}\n", style="dim")
        banner_text.append(f"Session: {self.session_id}\n\n", style="dim")

        if self.tool_categories_info:
            banner_text.append("Tools:\n", style="bold cyan")
            for category, tools in sorted(self.tool_categories_info.items()):
                banner_text.append(f"  [{category}]\n", style="bold dim")
                for tool in tools[:5]:
                    name = tool["name"]
                    desc = tool.get("description", "")
                    is_deferred = tool.get("defer_loading", False)
                    status_text = "(deferred)" if is_deferred else "(loaded)"
                    status_style = "yellow" if is_deferred else "green"
                    banner_text.append(f"    - {name} ", style="default")
                    banner_text.append(status_text, style=status_style)
                    if desc:
                        banner_text.append(f": {desc}\n", style="dim")
                    else:
                        banner_text.append("\n")
                if len(tools) > 5:
                    banner_text.append(f"    ... and {len(tools) - 5} more\n", style="dim")
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
        """渲染对话面板，将所有对话行组合为一个 Rich Panel。

        设计理由：
        - 使用 Text 对象逐行追加而非字符串拼接，因为 Text 对象保留每行的独立样式信息
        - Panel 提供视觉边框，将对话区域与其他 UI 元素（横幅、状态栏）分隔
        - conversation_lines 是预渲染的 Text 列表，此方法只做组合，不做样式计算
        """
        conversation_text = Text()
        for line in self.conversation_lines:
            conversation_text.append(line)
            conversation_text.append("\n")
        return Panel(conversation_text, title="Conversation", border_style="blue")

    def print_banner(self) -> None:
        """打印启动横幅和使用提示。

        设计理由：
        - 横幅展示模型、工具、技能等运行时信息，帮助用户确认环境配置
        - 提示信息独立于横幅面板，避免面板内容过于密集
        - 使用 console.print() 而非 logger，因为这是用户界面输出而非日志
        """
        self.console.print(self._render_banner())
        self.console.print()
        self.console.print("Type /quit to exit, /clear to clear history")
        self.console.print("Type /help for available commands")
        self.console.print()

    def add_message(self, role: str, content: str, is_tool: bool = False) -> None:
        """添加一条消息到对话显示区域并持久化存储。

        设计理由：
        - 同时完成 UI 渲染和存储持久化，保证显示与存储的一致性
        - is_tool 参数优先于 role 判断，因为工具消息可能以不同 role 出现
        - 使用 Rich Text 对象而非纯字符串，保留样式信息供后续渲染
        - 不同 role 使用不同前缀和颜色：
          - user: "> " 绿色（输入提示感）
          - assistant: "Hermes: " 白色（品牌标识）
          - tool: "⚡ " 青色（视觉突出）
          - system: 无前缀，dim 样式（辅助信息不抢视觉焦点）

        Args:
            role: 消息角色（user/assistant/system/tool）。
            content: 消息文本内容。
            is_tool: 是否为工具执行消息，优先于 role 使用工具样式。
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
        """显示工具开始执行的状态信息。

        设计理由：
        - 委托给 ActivityFeed 格式化，保持工具状态展示风格统一
        - 即时反馈让用户知道工具已开始执行，避免"卡住"的错觉
        """
        self.console.print(ActivityFeed.format_start(tool_name, action))

    def show_tool_complete(self, tool_name: str, action: str, elapsed: float) -> None:
        """显示工具执行完成的状态信息，包含耗时。

        设计理由：
        - elapsed 参数由调用方计算，此方法只负责展示，遵循单一职责
        - 耗时信息帮助用户判断工具性能，识别慢操作
        """
        self.console.print(ActivityFeed.format_complete(tool_name, action, elapsed))

    def show_tool_result_summary(self, tool_name: str, result: str) -> None:
        """根据工具类型解析结果并显示摘要信息。

        设计理由：
        - 不同工具的结果结构不同，需要按工具名分别解析关键字段
        - 使用 JSON 解析结果，因为工具返回值统一为 JSON 格式
        - 解析失败时降级为通用"completed"提示，而非报错：
          1. 结果摘要不是关键信息，失败不应中断对话
          2. 某些工具可能返回非 JSON 格式（如纯文本错误信息）
        - 各工具的摘要策略：
          - read_file: 显示读取行数（用户关心文件大小）
          - write_file: 显示写入字节数（确认写入成功）
          - search_files: 显示匹配文件数（评估搜索效果）
          - terminal: 显示退出码（判断命令是否成功）
          - todo: 委托给 _show_todo_list 专用渲染
        """
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
        """显示分隔线，标记 AI 回复的开始位置。

        设计理由：
        - 在工具执行日志和 AI 最终回复之间提供视觉分隔
        - 使用固定宽度 50 字符的横线，确保在不同终端宽度下都有良好表现
        - agent_name 参数化支持多 Agent 场景（如委托任务时显示子 Agent 名称）
        """
        self.console.print(f"┌─ {agent_name} " + "─" * 50, style="bold yellow")

    def clear_conversation(self) -> None:
        """清空对话显示区域和消息历史，保留系统提示。

        设计理由：
        - 保留 system role 的消息，因为系统提示是模型行为的基础配置
        - 清空 _last_reasoning 避免旧思考内容影响后续 debug 输出
        - conversation_lines 和 messages 同步清空，保持显示与数据一致
        """
        self.conversation_lines.clear()
        self.messages = [m for m in self.messages if m.get("role") == "system"]
        self._last_reasoning = ""

    def _print_status_bar(self) -> None:
        """渲染并打印状态栏，显示 token 使用量等运行时指标。

        设计理由：
        - 在每次消息处理后调用，让用户实时了解资源消耗
        - 额外打印空行，为下一次用户输入提供视觉间距
        """
        self.console.print(self.status_bar.render())
        self.console.print()

    # ========================================================================
    # 对话循环
    # ========================================================================

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
        - ConversationEventHandler 统一管理所有 TUI 对对话事件的订阅
        - 通过 register(events) 一次性注册，与 MemoryEventHandler 模式一致
        - 解耦 TUIApp 与事件订阅细节

        Memory 集成：
        - 如果 memory_manager 可用，创建 MemoryEventHandler 并注册到事件总线
        - MemoryEventHandler 会监听对话事件，自动触发记忆检索和刷写
        - prefetch_cache 包含预取的记忆上下文，需要注入到消息历史中
        """
        if not self.model_caller or not self.tool_dispatch:
            self.add_message("assistant", "This is a simulated response.", is_tool=False)
            return

        self.messages.append({"role": "user", "content": user_input})

        self._current_loop = ConversationLoop(
            model_call=self.model_caller,
            tool_dispatch=self.tool_dispatch,
            debug=self.debug,
        )
        loop = self._current_loop

        # 统一注册 TUI 事件处理器（模型调用 + 工具执行生命周期）
        conversation_handler = ConversationEventHandler(
            console=self.console,
            status_bar=self.status_bar,
            status_indicator=self.status_indicator,
            session_id=self.session_id,
            jsonl_store=self.jsonl_store,
            session_db=self.session_db,
        )
        conversation_handler.register(loop.events)

        # 注册 Memory 事件处理器
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

        # 自动压缩检查（任务 12.21）
        await self._check_auto_compress(result[0])

    async def _handle_command(self, command: str) -> bool:
        """处理斜杠命令，返回是否成功识别并处理了命令。

        设计理由：
        - 返回 bool 而非抛出异常，因为未识别的命令应交给对话循环处理（作为普通消息）
        - 使用 lower().strip() 标准化输入，容忍大小写和前后空格差异
        - /quit 和 /exit 同时支持带斜杠和不带斜杠形式，兼容用户习惯
        - 带参数的命令（/resume, /compress, /title）使用 split(None, 1) 拆分：
          - None 表示按任意空白字符分割（容忍多余空格）
          - 1 表示最多拆分一次（保留参数中的空格，如标题 "my project"）

        Args:
            command: 用户输入的原始命令字符串。

        Returns:
            True 表示命令已处理（不应作为普通消息发送），False 表示未识别。
        """
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
        """处理用户输入的消息或命令，是主循环的核心分发点。

        设计理由：
        - 以 "/" 开头判定为命令，否则为普通对话消息
        - 命令处理后立即打印状态栏，因为命令可能改变状态（如 /clear、/compress）
        - 普通消息先 add_message 再进入对话循环：
          1. add_message 同时完成 UI 显示和持久化
          2. 对话循环内部会将消息追加到 self.messages 列表
        - 对话完成后打印状态栏，反映最新的 token 使用量

        Args:
            message: 用户输入的原始文本（已 strip）。
        """
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
        """显示欢迎消息（当前为空实现，预留扩展点）。

        设计理由：
        - 预留 hook 方法，子类或未来版本可覆盖实现自定义欢迎消息
        - 当前不显示额外欢迎消息，因为 print_banner() 已提供足够的启动信息
        - state.welcomed 标志确保此方法只在首次循环时调用
        """
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
        from src.tools.core.registry import ToolRegistry

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
                if tool.defer_loading:
                    load_tag = "[yellow](deferred)[/yellow]"
                else:
                    load_tag = "[green](loaded)[/green]"
                self.console.print(f"    {status} [bold]{tool.name}[/bold] {load_tag}")
                if tool.description:
                    self.console.print(f"       [dim]{tool.description}[/dim]")
        self.console.print()

    async def shutdown(self) -> None:
        """执行 TUI 关闭时的清理操作。

        设计理由：
        - 在 finally 块中调用，确保无论何种退出方式（正常/Ctrl+C/异常）都执行清理
        - 清理顺序：停止标志 → 状态持久化 → 事件处理器清理
          1. 先设置 running=False，防止其他协程继续发起新操作
          2. 保存状态（如 session_id），支持下次启动时恢复
          3. 清理事件处理器订阅，避免内存泄漏（事件总线持有回调引用）
        """
        logger.info("TUI 正在关闭...")
        self.state.running = False
        self.state.save()
        self.event_handler.cleanup()
        logger.info("TUI 已关闭")


def create_tui(
    debug: bool = False,
    resume: str | None = None,
    resume_title: str | None = None,
    config: dict[str, Any] | None = None,
) -> TUIApp:
    """工厂函数：创建 TUIApp 实例。

    设计理由：
    - 生产环境只需传 debug/resume/config，TUIApp 内部自动初始化所有依赖
    - 保留工厂函数而非直接构造的原因：
      1. 统一入口，便于未来添加参数验证或 DI 容器
      2. 与 main.py 的调用约定保持一致
    """
    return TUIApp(
        debug=debug,
        resume=resume,
        resume_title=resume_title,
        config=config,
    )
