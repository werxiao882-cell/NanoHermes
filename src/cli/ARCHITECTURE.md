# CLI 模块架构

## 模块概述

CLI 模块提供 NanoHermes 的终端用户界面（TUI）。核心职责：接收用户输入、协调对话循环、渲染输出、管理子 Agent 状态。
模块以 `TUIApp`（tui.py）为门面（Facade），内部通过依赖注入组装多个子系统，外部只暴露 `TUIApp` 和 `create_tui()` 两个入口。

## 文件职责

```
src/cli/
├── __init__.py          # 模块导出，统一公共 API
├── tui.py               # TUI 主应用（组合根 + 对话循环 + 命令处理 + 渲染）
├── state.py             # 应用状态（TUIState）和工具调用记录（ToolCallRecord），JSON 持久化
├── event_handler.py     # 两个处理器：TUIEventHandler（用户输入）、ConversationEventHandler（对话事件订阅）
├── completers.py        # 输入补全：命令补全、文件路径补全、上下文感知路由
├── history.py           # 输入历史持久化（prompt_toolkit History 子类，JSON 存储）
├── streaming.py         # 流式输出：打字机效果、Markdown 增量渲染、状态指示器
├── layout.py            # 响应式布局（LayoutManager 监听 SIGWINCH）和动态面板管理
├── widgets.py           # UI 组件库：ANSI 控制、Panel、Spinner、StatusBar、ActivityFeed、ToolCallDisplay
├── agent_task.py        # 子 Agent 任务模型（AgentTask）和线程安全注册表（AgentTaskRegistry）
└── agent_printer.py     # 子 Agent 列表/transcript 打印器（增量打印 + bottom_toolbar）
```

## 核心数据流

```
用户输入 (prompt_toolkit PromptSession)
  │
  ▼
TUIApp.process_message()
  ├─ "/" 开头 → _handle_command() → 斜杠命令处理
  │     ├─ /help, /clear, /status, /sessions, /resume, /title
  │     ├─ /skills, /tools, /compress, /reasoning
  │     ├─ /agents, /agent <id> → AgentPrinter
  │     ├─ /loop, /stop-loop → LoopManager
  │     └─ /<skill-name> → 加载技能并触发对话
  │
  └─ 普通消息 → _run_conversation_loop()
        │
        ▼
      ConversationLoop (后台线程 via ThreadPoolExecutor)
        │
        ├─ EventBus 事件 ──────────────────────────────────┐
        │                                                  ▼
        │                              ConversationEventHandler.register()
        │                                ├─ MODEL_REQUEST  → StreamingStatusIndicator.start()
        │                                ├─ MODEL_RESPONSE → StatusBar 更新 token/耗时
        │                                ├─ TOOL_START     → ActivityFeed 打印 + 子Agent进度更新
        │                                ├─ TOOL_END       → 结果摘要打印 + 子Agent消息追加
        │                                ├─ MESSAGE_APPEND → 双存储持久化 (SQLite + JSONL)
        │                                ├─ DELEGATION_*   → AgentTaskRegistry 生命周期管理
        │                                └─ (MemoryEventHandler 独立注册)
        │
        ▼
      最终响应 → console.print() → 状态栏刷新
```

## 关键设计决策

### 1. 为什么用 prompt_toolkit 而非 curses/urwid？
prompt_toolkit 原生支持异步输入、自动补全、历史记录和快捷键，避免从零实现终端交互逻辑。
Rich 负责输出渲染，prompt_toolkit 负责输入管线，两者职责分离。

### 2. 为什么 ConversationLoop 在后台线程运行？
LLM API 调用是同步阻塞的（OpenAI SDK），会阻塞 asyncio 事件循环。
通过 ThreadPoolExecutor 在后台线程运行，主线程用 `asyncio.sleep(0.1)` 轮询完成状态，
同时保持对 Ctrl+C 中断的响应。

### 3. 为什么双存储（SQLite + JSONL）？
- SQLite：支持 SQL 查询、FTS5 全文搜索、会话列表浏览
- JSONL：保留完整消息结构（tool_calls、reasoning、usage），支持会话精确恢复
两者独立 try-except，一个失败不影响另一个。

### 4. 为什么子 Agent 事件不直接打印到主输出？
子 Agent 在后台线程运行，其工具调用和消息如果混入主输出会造成混乱。
通过 `child_task_id` 字段区分事件来源，子 Agent 事件只更新 AgentTaskRegistry，
用户通过 `/agent <id>` 命令按需查看 transcript（增量打印模式）。

### 5. 为什么用 _UNSET 哨兵区分构造参数？
`session_db=_UNSET` 区分"未传参"（自动初始化完整依赖链）和"显式传 None"（测试场景无需数据库），
让同一个构造函数同时服务生产环境和单元测试。

### 6. 为什么事件处理集中在 ConversationEventHandler？
将散落的多处 `loop.events.on()` 调用集中到单一类，通过 `register(events)` 一行完成所有订阅，
与 MemoryEventHandler 的注册模式保持一致，解耦 TUIApp 与事件订阅细节。

## 对外接口

### 公共类和函数

| 接口 | 说明 |
|------|------|
| `TUIApp` | TUI 主应用类，包含 `run()`, `process_message()`, `shutdown()` |
| `create_tui(debug, resume, resume_title, config)` | 工厂函数，创建 TUIApp 实例 |
| `TUIState` | 应用状态 dataclass（running, session_id, tool_calls, layout） |
| `ToolCallRecord` | 工具调用记录 dataclass |
| `TUIEventHandler` | 用户输入事件处理器 |
| `ConversationEventHandler` | ConversationLoop 事件订阅处理器 |
| `ContextAwareCompleter` | 上下文感知补全器（路由到命令/文件补全） |
| `CommandCompleter` | 斜杠命令补全器（支持技能名补全） |
| `FilePathCompleter` | 文件路径补全器 |
| `TUIHistory` | 输入历史持久化（prompt_toolkit History 子类） |
| `TypewriterEffect` | 打字机效果（逐字输出） |
| `StreamingMarkdown` | 流式 Markdown 渲染 |
| `StreamingStatusIndicator` | 流式状态指示器（KawaiiSpinner） |
| `LayoutManager` / `LayoutConfig` | 响应式布局管理 |
| `DynamicPanelManager` | 动态面板管理 |
| `StatusBar` | 状态栏（token 用量、耗时） |
| `ActivityFeed` | 工具调用活动流显示 |
| `AgentTask` / `AgentTaskRegistry` | 子 Agent 任务模型和线程安全注册表 |
| `AgentPrinter` | 子 Agent 列表和 transcript 打印器 |

### 主要 Widget 组件

`Panel`, `Spinner`, `KawaiiSpinner`, `ProgressBar`, `ToolCallDisplay`,
`ToolCallHistoryPanel`, `ToolCallResultSummary`, `styled_text`,
`get_terminal_size`, `clear_screen`, `set_color`, `move_cursor`, `ANSI_COLORS`

## 依赖关系

### 依赖的其他 src/ 模块

| 模块 | 用途 |
|------|------|
| `src.config` | 配置加载（load_config, get_api_key, get_base_url） |
| `src.provider.openai_client` | LLM 客户端封装 |
| `src.conversation.loop` | 核心对话循环（ConversationLoop） |
| `src.conversation.events` | 事件总线（EventBus, EventType） |
| `src.conversation.assembler` | 系统提示组装（PromptAssembler） |
| `src.tools.core.registry` | 工具注册表（ToolRegistry, get_tool_schemas） |
| `src.tools.core.dispatcher` | 工具调度（dispatch） |
| `src.skills.manager` | 技能管理（SkillManager） |
| `src.skills.preprocessing` | 技能内容预处理 |
| `src.session.session_db` | SQLite 会话存储 |
| `src.session.jsonl_store` | JSONL 消息存储 |
| `src.memory` | 记忆管理（MemoryManager, FileMemoryProvider, MemoryStore） |
| `src.memory.event_handler` | 记忆事件处理器（MemoryEventHandler） |
| `src.delegation` | 委托管理（init_manager） |
| `src.compression` | 上下文压缩（ContextCompressor） |
| `src.background` | 后台任务调度（BackgroundTaskScheduler） |
| `src.loop` | 循环执行器（LoopManager, LoopConfig, LoopMode） |

### 外部依赖

- **prompt_toolkit** — 终端输入管线（PromptSession, Completer, History, KeyBindings）
- **rich** — 终端输出渲染（Console, Panel, Text, Markdown, Rule）
- **openai** — LLM SDK 客户端
