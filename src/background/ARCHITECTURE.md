# Background Task Scheduler Architecture

## Responsibility
统一的后台任务调度框架，管理记忆刷写、技能审查等后台任务。
在对话循环结束后评估触发条件，满足则在守护线程中异步执行。

## 目录结构

```
src/background/
├── __init__.py          # 模块入口，re-export BackgroundTaskScheduler
└── scheduler.py         # BackgroundTaskScheduler（信号量并发 + 事件驱动触发）
```

## Components

```
┌──────────────────────────────────────────────────────────────┐
│              BackgroundTaskScheduler                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Task Registry                                          │  │
│  │  - register_task(name, handler, trigger, enabled)      │  │
│  │  - unregister_task(name)                               │  │
│  │  - set_task_enabled(name, enabled)                     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Event-Driven Trigger                                   │  │
│  │  - on_loop_end(messages, iteration) → evaluate all     │  │
│  │  - 每个 task 的 trigger(event_data) → bool             │  │
│  │  - 满足条件 → 启动守护线程执行                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Concurrency Control                                    │  │
│  │  - threading.Semaphore(max_concurrent=2)               │  │
│  │  - 运行中任务去重（同名任务不重复启动）                 │  │
│  │  - 任务超时保护（默认 300s）                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Task History                                           │  │
│  │  - deque(maxlen=20) 最近 20 条记录                     │  │
│  │  - 记录：name, start_time, duration, success, error    │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

1. 对话循环结束时调用 `scheduler.on_loop_end(messages, iteration)`
2. 遍历所有已注册的 enabled 任务
3. 检查任务是否已在运行（去重）
4. 调用 `task.trigger(event_data)` 评估触发条件
5. 满足条件 → 启动守护线程（daemon=True）
6. 线程内：获取信号量 → 执行 handler → 记录历史 → 释放信号量
7. 应用退出时调用 `scheduler.shutdown(timeout)` 等待任务完成

## 已注册任务

| 任务名 | 来源模块 | 触发条件 | 处理器 |
|--------|---------|---------|--------|
| `memory_flush` | `src/memory/flush_task.py` | 消息数 >= 10 | fork_agent 提取记忆 |
| `skill_review` | `src/skills/review_task.py` | 轮数 >= 10 且间隔 >= 30min | fork_agent 审查技能 |

## Design Decisions

| Decision | Reason |
|----------|--------|
| **threading.Semaphore 控制并发** | 比 asyncio 更简单可靠，项目整体使用同步架构 |
| **事件驱动触发（LOOP_END）** | 比定时轮询更高效，只在对话结束时评估 |
| **守护线程执行** | daemon=True 确保主线程退出时后台线程自动终止 |
| **任务失败只记录日志** | 后台任务不应影响主对话流程 |
| **同名任务去重** | 防止同一任务被重复触发（如长时间运行的记忆刷写） |
| **历史 deque(maxlen=20)** | 固定内存占用，最近 20 条足够调试 |

## Dependencies

- Internal: src/memory/flush_task.py, src/skills/review_task.py
- External: threading (stdlib)
