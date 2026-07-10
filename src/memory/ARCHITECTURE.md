# Memory 模块架构

## 模块概述

可插拔的跨会话记忆系统。以 `MemoryStore` 为唯一数据源，通过 `MemoryProvider` 抽象基类
定义 15 个方法的标准接口，`MemoryManager` 编排多提供者生命周期并直接订阅对话循环事件总线。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块入口，re-export 公共 API |
| `provider.py` | `MemoryProvider` 抽象基类（15 个方法：4 抽象 + 11 可选） |
| `memory_store.py` | 唯一数据源：§ 分隔符解析、文件锁、原子写入、漂移检测、冻结快照、威胁扫描 |
| `file_provider.py` | `FileMemoryProvider`：内置文件提供者，全部操作委托 `MemoryStore` |
| `manager.py` | `MemoryManager` 编排器：Fan-out 容错、单外部提供者限制、工具路由、EventBus 集成 |

## 核心数据流

```
会话启动
  LOOP_START
    └→ MemoryManager._on_loop_start
         └→ MemoryManager.initialize_all
              └→ FileMemoryProvider.initialize
                   └→ MemoryStore.load_from_disk → 捕获冻结快照

每轮对话（仅首次迭代 iteration=1）
  ITERATION_START
    └→ MemoryManager._on_iteration_start
         ├→ MemoryManager.on_turn_start_all → providers.on_turn_start
         └→ MemoryManager.prefetch_all → providers.prefetch
              └→ FileMemoryProvider.prefetch
                   └→ MemoryStore.format_for_system_prompt（返回冻结快照）
              结果包裹 <memory-context> 标签

对话结束（中断时跳过）
  LOOP_END
    └→ MemoryManager._on_loop_end
         ├→ MemoryManager.sync_all → providers.sync_turn
         └→ MemoryManager.queue_prefetch_all → providers.queue_prefetch

memory 工具调用
  Agent → MemoryManager.handle_tool_call("memory", args)
    └→ FileMemoryProvider.handle_tool_call
         └→ MemoryStore.add / replace / remove
              流程：威胁扫描 → 文件锁 → 漂移检测 → 操作 → 原子写入

上下文压缩前
  PRE_COMPRESS → MemoryManager._on_pre_compress
    └→ MemoryManager.on_pre_compress_all → providers.on_pre_compress
         提取内容写入 data["extracted_memory"]

会话关闭（由外部直接调用，非事件总线驱动）
  MemoryManager.on_session_end_all(messages) → providers.on_session_end
  MemoryManager.shutdown_all() → providers.shutdown
```

## 关键设计决策

| 决策 | 理由 |
|------|------|
| **MemoryStore 为唯一数据源** | 原三条并行读写路径各自操作文件，数据一致性无法保证；统一委托确保原子性 |
| **冻结快照** | Anthropic prompt caching 要求系统提示前缀稳定；`load_from_disk()` 时捕获一次，会话内不变，工具调用只修改实时状态 |
| **原子写入（tempfile + os.replace）** | `open("w")` 先截断再写入，中途崩溃则数据丢失；原子写入保证读者始终看到完整的旧或新文件 |
| **单独 .lock 文件而非锁原文件** | 记忆文件使用原子写入（temp + replace），锁原文件会阻塞 replace；单独 .lock 不影响写入流程 |
| **跨平台文件锁降级** | Unix 用 fcntl，Windows 用 msvcrt，都不可用时降级无锁（单用户场景可接受） |
| **漂移检测 + .bak 备份** | 用户可能手动编辑记忆文件；往返序列化不匹配或单条目超限时拒绝覆盖并创建备份 |
| **威胁模式扫描** | 10 种正则检测 prompt 注入/角色劫持/密钥渗出，外加不可见 Unicode 字符检测 |
| **Fan-out 容错** | 每个 provider 独立 try/except，一个失败不影响其他 provider 和主对话流程 |
| **单外部提供者限制** | 多外部 provider 的 prefetch 结果可能冲突，tool schema 可能重名，成本线性增长 |
| **EventBus 直接订阅** | MemoryManager 直接注册到 EventBus，减少 MemoryEventHandler 薄适配层，简化架构 |
| **中断轮次不同步** | 部分助手输出、中止的工具链不是完整对话事实，持久化会污染记忆 |
| **FileMemoryProvider 纯委托** | 重构前自有读写逻辑，重构后全部委托 MemoryStore，自身只负责生命周期适配 |

## 对外接口

```python
# 数据存储（供 memory_tool 等直接调用）
from src.memory import MemoryStore

# 抽象基类（外部 provider 实现此接口）
from src.memory import MemoryProvider        # 15 个方法，4 个抽象

# 编排器（直接订阅 EventBus）
from src.memory import MemoryManager         # add_provider / register(events) / handle_tool_call / *_all

# 内置提供者
from src.memory import FileMemoryProvider    # name="builtin"，委托 MemoryStore
```

**MemoryStore 公共方法**：`load_from_disk()`, `add(target, content)`, `replace(target, old, new)`,
`remove(target, old)`, `format_for_system_prompt(target)`

**辅助函数**（memory_store.py）：`get_session_summary_path()`, `get_agent_memory_path()`,
`get_team_memory_path()` — 多层记忆路径计算

## 依赖关系

**模块内依赖**：
```
manager → provider (ABC)
manager → conversation.events (EventBus, EventType)
file_provider → provider (ABC)
file_provider → memory_store（委托）
```

**外部模块依赖**：
- `src.conversation.events` — `EventBus`, `EventType`（manager.py 直接订阅事件总线）

**无外部第三方依赖**（仅 Python 标准库：abc, pathlib, tempfile, os, re, json, logging, time, contextlib）

## 配置常量

```python
MEMORY_CHAR_LIMIT = 2200   # MEMORY.md 最大字符数
USER_CHAR_LIMIT = 1375     # USER.md 最大字符数
```
