# Loop 模块架构

## 模块概述

循环执行模块，提供 `/loop` 命令支持，让 AI Agent 在会话内自动重复执行任务。
支持固定间隔和动态间隔两种模式，循环作用域限定在当前会话，7 天自动过期，支持 `--resume` 恢复。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 定义数据类型（LoopMode、LoopStatus、LoopConfig、LoopState）和常量 |
| `interval_parser.py` | 解析间隔表达式（持续时间/自然语言/Cron）为秒数，格式化秒数为可读字符串 |
| `prompt.py` | 加载维护提示：`.claude/loop.md` → `~/.nanohermes/loop.md` → 内置提示 |
| `manager.py` | 循环生命周期管理：创建、调度执行、停止、恢复，通过回调通知 TUI |

## 核心数据流

```
用户输入 /loop 5m "检查部署"
    │
    ▼
TUI 解析参数 → LoopManager.create_loop(interval="5m", prompt="检查部署")
    │                                       │
    │                    interval_parser.parse_interval("5m") → 300
    │                    prompt.get_maintenance_prompt() （prompt=None 时）
    │                                       │
    │                                       ▼
    │                              LoopConfig + LoopState 创建
    │                                       │
    ▼                                       ▼
emit "created" 事件 ──────────────→ TUI 显示确认信息
    │
    ▼
LoopManager.start_loop(run_conversation)
    │
    ▼
_run_loop() asyncio Task 循环：
    │
    ├── 检查过期（7 天）/ 停止信号
    ├── emit "executing" → run_conversation(prompt)
    ├── 动态模式：正则提取 __next_interval: Nm__ 标记
    ├── emit "waiting" → asyncio.wait_for(stop_event, timeout=间隔秒数)
    └── 出错：emit "error" → 等待后重试（不停止循环）
    │
    ▼
用户 /stop-loop → LoopManager.stop_loop() → emit "stopped"
```

## 关键设计决策

### 为什么独立模块而非扩展 cronjob 工具？

循环是会话级的（复用当前上下文，与 TUI 紧密集成），cronjob 是全局的（新会话执行）。
保持单一职责，避免工具文件膨胀。

### 为什么用 asyncio Task 而非线程？

TUI 使用 asyncio 事件循环（prompt_toolkit），Task 可通过 `task.cancel()` 取消，
与异步模型兼容，避免线程同步问题。

### 为什么单次失败不停止循环？

网络错误、API 限流等临时故障不应终止循环。错误通过事件回调通知 TUI，
等待间隔后自动重试，用户可手动 `/stop-loop`。

### 为什么间隔限制在 60 秒 ~ 24 小时？

最小 60 秒防止 API 滥用，最大 24 小时防止用户忘记停止循环。
秒级值自动向上取整到 60 的倍数（cron 最小粒度是分钟）。

### 为什么动态模式下每次迭代重新加载 loop.md？

支持运行时修改循环策略，无需重启 Agent。25,000 字节截断防止过大文件。

## 对外接口

### 数据类型（`src.loop`）

- `LoopMode` — 调度模式枚举：FIXED / DYNAMIC
- `LoopStatus` — 生命周期枚举：CREATED / ACTIVE / WAITING / EXECUTING / STOPPED / EXPIRED / ERROR
- `LoopConfig` — 不可变配置（loop_id, interval_seconds, prompt, mode, created_at），支持 `to_meta_dict()` / `from_meta_dict()` 序列化
- `LoopState` — 可变状态（config, status, execution_count, last_executed_at, last_error）
- `generate_loop_id()` — 生成 8 字符唯一 ID

### 间隔解析（`src.loop.interval_parser`）

- `parse_interval(expression: str) -> int` — 解析为秒数
- `format_interval(seconds: int) -> str` — 格式化为 "5m" / "2h" / "1d"
- `IntervalParseError` — 解析失败异常

### 提示加载（`src.loop.prompt`）

- `get_maintenance_prompt(working_dir: Path | None) -> str` — 按优先级加载维护提示

### 循环管理（`src.loop.manager`）

- `LoopManager(working_dir, on_loop_event)` — 生命周期管理器
  - `create_loop(interval, prompt) -> LoopState` — 创建循环（自动停止已有循环）
  - `start_loop(run_conversation) -> None` — 启动 asyncio Task 执行器
  - `stop_loop() -> LoopState | None` — 停止循环
  - `restore_loop(config) -> LoopState` — 从元数据恢复（--resume）
  - `active_loop` / `is_running` — 状态查询属性

### 常量

- `MIN_INTERVAL_SECONDS = 60`、`MAX_INTERVAL_SECONDS = 86400`
- `LOOP_EXPIRY_DAYS = 7`、`LOOP_ID_LENGTH = 8`
- `DEFAULT_DYNAMIC_INTERVAL = 600`（10 分钟）、`MAX_LOOP_MD_SIZE = 25_000`

## 依赖关系

```
src/loop/
├── 依赖: 仅 Python 标准库（asyncio, re, dataclasses, enum, pathlib, uuid, datetime）
├── 被依赖: src/cli/tui.py（/loop、/stop-loop 命令处理）
└── 被依赖: src/main.py（依赖注入 LoopManager 到 TUI）
```
