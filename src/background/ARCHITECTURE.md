# Background 模块架构

## 模块概述

后台任务调度框架，在对话循环结束后异步执行审查任务（记忆刷写、技能审查）。
核心由三部分组成：调度器（scheduler）、审查引擎（review）、具体任务（memory_flush / skill_review）。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块入口，re-export 所有公共 API |
| `scheduler.py` | `BackgroundTaskScheduler`——信号量并发控制、事件驱动触发、任务注册/历史 |
| `review.py` | 审查引擎——`fork_agent()` 工具调用循环、`run_background_review()` 同步入口、提示模板 |
| `memory_flush.py` | 记忆刷写任务——handler/trigger/注册函数，将 memory 工具路由到 FileMemoryProvider |
| `skill_review.py` | 技能审查任务——handler/trigger/注册函数，通过 skill_manage 工具创建或更新技能 |

## 核心数据流

```
ConversationLoop.run() 结束一轮迭代
        │
        ▼
scheduler.on_loop_end(messages, iteration, **kwargs)
        │
        ▼  遍历已注册任务
  ┌─────┴─────┐
  │ trigger() │  评估触发条件（消息数/轮数/时间间隔）
  └─────┬─────┘
        │ 满足条件
        ▼
  启动守护线程 (daemon=True)
        │
        ▼  获取 Semaphore
  handler(event_data)
        │
        ▼
  run_background_review(messages, model_call, tool_dispatch, review_type)
        │
        ├─► format_conversation()       # 截断每条消息到 500 字符
        ├─► build_review_prompt()       # 选择 MEMORY / SKILL 模板
        └─► fork_agent()                # 工具调用循环（最多 5 轮）
                │
                ├─► model_call(messages, filtered_schemas)
                ├─► tool_dispatch(name, args)   # 白名单过滤
                └─► 返回 {final_response, iterations}
```

## 关键设计决策

| 决策 | 原因 |
|------|------|
| **threading.Semaphore 控制并发** | 项目整体使用同步架构，比 asyncio 更简单可靠 |
| **事件驱动触发（on_loop_end）** | 比定时轮询更高效，只在对话结束时评估 |
| **守护线程（daemon=True）** | 主线程退出时后台线程自动终止，无需手动清理 |
| **同名任务去重** | 防止长时间运行的任务被重复触发 |
| **fork_agent 工具白名单** | 审查 Agent 只能使用 memory/skill_manage/skill_view/skills_list，避免副作用 |
| **MAX_FORK_ITERATIONS=5** | 防止审查 Agent 陷入无限工具调用循环 |
| **memory_dispatch 路由** | 记忆刷写时将 memory 工具直接路由到 FileMemoryProvider，绕过主 Dispatcher |
| **任务失败只记录日志** | 后台任务不应影响主对话流程 |
| **历史 deque(maxlen=20)** | 固定内存占用，最近 20 条足够调试 |
| **register_*_task 闭包注入依赖** | 避免 handler 直接依赖全局变量，通过闭包捕获依赖 |

## 对外接口

### 调度器

- `BackgroundTaskScheduler(max_concurrent, task_timeout_seconds, enabled)`
  - `.register_task(name, handler, trigger, enabled)`
  - `.unregister_task(name) -> bool`
  - `.set_task_enabled(name, enabled) -> bool`
  - `.on_loop_end(messages, iteration, **kwargs) -> list[str]`
  - `.get_running_tasks() -> list[dict]`
  - `.get_task_history(limit) -> list[dict]`
  - `.get_registered_tasks() -> list[dict]`
  - `.shutdown(timeout)`
  - `.reset()`

### 审查引擎

- `run_background_review(messages, model_call, tool_dispatch, review_type, ...)`
- `spawn_background_review(messages, model_call, tool_dispatch, review_type, ...)`
- `fork_agent(messages, model_call, tool_dispatch, ...)`
- `build_review_prompt(review_type, conversation) -> str`
- `format_conversation(messages, max_chars) -> str`

### 任务注册

- `register_memory_flush_task(scheduler, memory_provider, model_caller, tool_dispatch, ...)`
- `register_skill_review_task(scheduler, model_caller, tool_dispatch, ...)`

### 常量

- `REVIEW_TOOL_WHITELIST`: `{"memory", "skill_manage", "skill_view", "skills_list"}`
- `MEMORY_FLUSH_MIN_MESSAGES`: 10
- `SKILL_REVIEW_MIN_TURNS`: 10
- `SKILL_REVIEW_MIN_INTERVAL_SECONDS`: 1800

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `threading` (stdlib) | 守护线程、信号量、锁 |
| `src/memory/` (FileMemoryProvider) | 记忆刷写时通过 `memory_provider.handle_tool_call()` 写入记忆 |
| `src/tools/` (tool_dispatch) | 技能审查时通过工具分发器调用 skill_manage 等工具 |
| `src/provider/` (model_caller) | 调用 LLM 进行审查 |
