# Multi-Agent Delegation 模块架构

## 模块概述

多 Agent 委托管理器：父 Agent 委托任务给隔离子 Agent，支持单任务（阻塞）、批量并行、后台非阻塞三种模式。
通过角色系统（LEAF/ORCHESTRATOR）控制权限边界，信号量+深度限制防止资源耗尽，全局单例提供统一访问。

## 文件职责

```
src/delegation/
├── __init__.py        # 全局单例管理（init_manager / get_manager / reset_manager）
├── types.py           # AgentRole 枚举、DelegationResult/ChildAgentConfig 数据类、工具阻止列表常量
├── semaphore.py       # 自定义信号量：同步/异步双模式，支持 with 上下文管理器
├── notification.py    # task-notification XML 格式化：子 Agent 结果回流到主 Agent
└── manager.py         # DelegationManager 核心：委托入口、角色过滤、子 Agent 执行、JSONL 录制、事件转发
```

## 核心数据流

### 同步委托

```
delegate_task(goal/tasks)
    │
    ├── 深度检查: current_depth >= max_spawn_depth → 返回错误
    │
    ├── 单任务: delegate_single()
    │       ├── build_child_agent_config() → 过滤工具 + 构建系统提示
    │       ├── Semaphore 获取槽位（with 语句）
    │       ├── emit(DELEGATION_START) → 内部 + 父 EventBus
    │       ├── _execute_single_agent(config)
    │       │       ├── 创建独立 child_messages + 过滤后 child_tools
    │       │       ├── 创建子 ConversationLoop（注入 model_caller + tool_dispatch）
    │       │       ├── JSONL 录制 → ~/.nanohermes/agents/{parent}__{task_id}.jsonl
    │       │       ├── 事件转发 → 父 EventBus（TOOL_START/END + child_task_id）
    │       │       ├── 独立线程运行 child_loop.run()
    │       │       └── threading.Event.wait(timeout) → DelegationResult
    │       └── emit(DELEGATION_COMPLETE / DELEGATION_FAIL)
    │
    └── 批量: delegate_batch()
            ├── 有事件循环 → asyncio.gather 并行 + run_in_executor
            └── 无事件循环 → 串行执行
```

### 后台委托（非阻塞）

```
delegate_background(goal, name) → 立即返回 task_id
    ├── emit(DELEGATION_START) → TUI 注册 AgentTask
    └── 后台守护线程: child_loop.run() → emit(DELEGATION_COMPLETE/FAIL)
```

### 子 Agent 隔离

```
Parent Agent                          Child Agent (独立线程)
  messages: [完整对话]                   messages: [system(角色), user(goal)]
  tools: [全部]         ──委托──→       tools: [过滤后] ← 排除 BLOCKED_TOOLS
  EventBus: parent                     EventBus: child (独立实例)
                                       │
                                       ├→ JSONL: agents/{parent}__{task_id}.jsonl
                                       └→ 事件转发 → parent（注入 child_task_id）
```

## 关键设计决策

**全局单例**：DelegationManager 需注入 model_caller、tool_dispatch 等多个依赖，`init_manager()` 在 TUI 启动时调用一次，其他模块通过 `get_manager()` 获取，避免到处传递依赖。

**自定义 Semaphore**：项目同时有同步上下文（CLI prompt_toolkit）和异步上下文（MCP 服务器），`asyncio.Semaphore` 在同步代码中会抛 RuntimeError。自定义实现提供 `acquire_sync`/`acquire` 双套 API，用计数器+轮询替代事件循环依赖。

**同步阻塞等待**：`threading.Event.wait(timeout)` 简化控制流，超时保护防死锁。后台模式 `delegate_background` 提供非阻塞选项。

**角色权限控制**：LEAF 禁止 `delegate_task`（防无限递归）、`clarify`（不打扰用户）、`memory`（防写入冲突）、`execute_code`（降低风险）。ORCHESTRATOR 额外允许 `delegate_task`，受 `max_spawn_depth` 限制。

**事件转发**：子 Agent 在独立线程+独立 EventBus 中运行，TUI 只订阅父 EventBus。转发 TOOL_START/END/MESSAGE_APPEND 并注入 `child_task_id`，TUI 据此区分主/子 Agent。

**JSONL 独立目录**：子 Agent 写入 `~/.nanohermes/agents/`（非 `sessions/`），双下划线 `{parent}__{task_id}` 确保命名无歧义。

**批量同步/异步自适应**：`delegate_batch()` 检测事件循环状态，有循环走 `asyncio.gather` 并行，无循环走串行，避免 RuntimeError。

## 对外接口

### 全局单例（`__init__.py`）

- `init_manager(model_caller, tool_dispatch, tool_schemas, ...) → DelegationManager` — TUI 启动时调用
- `get_manager() → DelegationManager | None` — 其他模块获取
- `reset_manager()` — 测试清理

### 数据类型（`types.py`）

- `AgentRole` — 枚举：`LEAF` / `ORCHESTRATOR`
- `DelegationResult` — task_id, success, summary, error, role, duration, tool_calls
- `ChildAgentConfig` — task_id, role, goal, context, blocked_tools, system_prompt, timeout, parent_session_id
- `DELEGATE_BLOCKED_TOOLS` — frozenset: `{delegate_task, clarify, memory, execute_code}`
- `ORCHESTRATOR_ALLOWED_TOOLS` — frozenset: `{delegate_task}`

### DelegationManager 公共方法

- `delegate_task(goal?, tasks?, role?, toolsets?, context?)` — 统一入口
- `delegate_single(goal, role?, toolsets?, context?)` — 单任务阻塞委托
- `delegate_batch(tasks, role?, toolsets?)` — 批量并行委托
- `delegate_background(goal, role?, toolsets?, context?, name?)` — 后台非阻塞委托
- `build_child_agent_config(goal, role, toolsets?, context?)` — 构建子 Agent 配置
- `filter_blocked_tools(role, toolsets?)` — 过滤被阻止的工具
- `set_parent_context(parent_event_bus?, parent_session_id?)` — 延迟注入父上下文
- `set_auto_deny_callback(callback)` / `set_auto_approve_callback(callback)`
- `get_active_children()` / `get_completed_results()` / `reset()`

### Semaphore 公共方法

- `Semaphore(max_concurrent=3)` — 自动检测同步/异步上下文
- `acquire_sync() → bool` / `release_sync()` — 同步 API
- `async acquire()` / `async release()` — 异步 API
- `active_count` / `available_slots` — 状态查询
- `__enter__` / `__exit__` — with 上下文管理器

### 通知格式（`notification.py`）

- `format_task_notification(task_id, status, summary, tool_calls, duration_s) → str` — XML 格式

## 依赖关系

### 依赖的 src/ 模块

| 模块 | 用途 |
|------|------|
| `src.conversation.loop` | 创建子 Agent 独立的 ConversationLoop |
| `src.conversation.events` | EventBus + EventType（事件发射和转发） |
| `src.session.jsonl_store` | 子 Agent JSONL 录制到 agents/ 目录 |

### 被其他模块依赖

| 模块 | 用途 |
|------|------|
| `src.tools.impls.delegation_tool` | delegate_task 工具调用 `get_manager().delegate_task()` |
| `src.cli` | TUI 初始化调用 `init_manager()`，事件处理器订阅 DELEGATION_* 事件 |
| `src.main` | 组合根，注入依赖到 `init_manager()` |
