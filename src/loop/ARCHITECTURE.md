# Loop 模块架构

循环执行模块，提供 `/loop` 命令支持。

## 职责

- 解析间隔表达式（`5m`, `every 2 hours`, `*/5 * * * *`）
- 管理循环生命周期（创建、执行、停止、恢复）
- 加载内置维护提示或 `loop.md` 自定义提示
- 从 AI 响应中提取动态间隔标记

## 组件

### `__init__.py` — 数据类型

- `LoopMode`: 调度模式枚举（FIXED / DYNAMIC）
- `LoopStatus`: 生命周期状态枚举
- `LoopConfig`: 不可变配置（间隔、提示、模式、过期时间）
- `LoopState`: 可变运行时状态（执行计数、最后错误）
- `generate_loop_id()`: 生成 8 字符唯一 ID

### `interval_parser.py` — 间隔解析器

- `parse_interval(expression)`: 解析间隔表达式为秒数
- `format_interval(seconds)`: 秒数格式化为人类可读字符串
- 支持格式：持续时间（`5m`）、自然语言（`every 2 hours`）、Cron（`*/5 * * * *`）

### `prompt.py` — 提示系统

- `get_maintenance_prompt(working_dir)`: 获取维护提示
- 查找顺序：`.claude/loop.md` → `~/.nanohermes/loop.md` → 内置提示
- 25,000 字节截断限制

### `manager.py` — 循环管理器

- `LoopManager`: 循环生命周期管理
- `create_loop()`: 创建循环
- `start_loop()`: 启动后台执行器（asyncio Task）
- `stop_loop()`: 停止循环
- `restore_loop()`: 从元数据恢复（用于 --resume）
- 事件回调机制通知 TUI 状态变化

## 数据流

```
用户输入 /loop 5m "检查部署"
    │
    ▼
TUI._cmd_loop() 解析参数
    │
    ▼
LoopManager.create_loop(interval="5m", prompt="检查部署")
    │
    ▼
emit "created" 事件 → TUI 显示确认信息
    │
    ▼
LoopManager.start_loop(run_conversation)
    │
    ├── 等待 5 分钟
    ├── run_conversation("检查部署")
    ├── 显示结果
    └── 重复...
    │
    ▼
用户输入 /stop-loop
    │
    ▼
LoopManager.stop_loop() → emit "stopped" 事件
```

## 依赖关系

```
src/loop/
├── 依赖: 无（纯 Python 标准库 + 项目数据类型）
├── 被依赖: src/cli/tui.py（命令处理）
└── 被依赖: src/main.py（依赖注入）
```

## 设计决策

### 为什么独立模块而非扩展 cronjob？

- 循环是会话级的，cronjob 是全局的
- 循环复用当前上下文，cronjob 在新会话中执行
- 循环需要与 TUI 紧密集成（状态显示、进度指示）
- 保持单一职责，避免工具文件过大

### 为什么用 asyncio Task 而非线程？

- TUI 本身使用 asyncio 事件循环
- Task 可以被取消（`task.cancel()`），线程取消更复杂
- 与 `prompt_toolkit` 的异步模型兼容
- 避免线程同步问题

### 为什么单次失败不停止循环？

- 网络错误、API 限流等临时问题不应终止循环
- 错误信息通过事件回调通知 TUI 显示
- 等待间隔后自动重试
- 用户可手动 `/stop-loop` 停止
