# Memory System Architecture

## Responsibility
可插拔的记忆后端系统，支持跨会话持久记忆。
通过 MemoryProvider 抽象基类定义标准接口，MemoryManager 编排多个提供者。
内置文件提供者使用 MEMORY.md/USER.md 存储记忆，预留外部 provider 接口（Honcho、Mem0 等）。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    MemoryManager                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Provider Registration                                  │  │
│  │  - add_provider(): 注册提供者                           │  │
│  │  - 单外部提供者限制（非 builtin 名称）                  │  │
│  │  - 工具 schema 路由映射                                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Fan-out 容错生命周期调用                               │  │
│  │  - initialize_all(): 初始化所有提供者                   │  │
│  │  - build_system_prompt(): 构建系统提示                  │  │
│  │  - prefetch_all(): 预取记忆上下文（包裹标签）           │  │
│  │  - sync_all(): 同步对话内容                             │  │
│  │  - shutdown_all(): 关闭所有提供者                       │  │
│  │  - 每个 provider 独立 try/except，失败不影响其他        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  事件钩子 Fan-out                                       │  │
│  │  - on_turn_start_all(): 每轮对话开始                    │  │
│  │  - on_session_end_all(): 会话结束                       │  │
│  │  - on_pre_compress_all(): 压缩前提取信息                │  │
│  │  - on_delegation_all(): 子代理完成                      │  │
│  │  - on_memory_write_all(): Mirror hook（双轨同步）       │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                          ▲
                          │ 实现
┌──────────────────────────────────────────────────────────────┐
│                    MemoryProvider (ABC)                       │
│                                                              │
│  核心抽象方法（4 个，必须实现）：                              │
│  - name: 提供者名称标识                                      │  │
│  - is_available: 依赖检查                                    │  │
│  - initialize: 会话初始化                                    │  │
│  - system_prompt_block: 系统提示文本块                       │  │
│                                                              │
│  数据流方法（4 个，默认空实现）：                              │
│  - prefetch: 预取相关记忆                                    │  │
│  - queue_prefetch: 后台预取排队                              │  │
│  - sync_turn: 同步对话内容                                   │  │
│  - shutdown: 清理关闭                                        │  │
│                                                              │
│  事件钩子（5 个，可选覆盖）：                                  │
│  - on_turn_start: 每轮对话开始                               │  │
│  - on_session_end: 会话结束归档                              │  │
│  - on_pre_compress: 压缩前提取信息                           │  │
│  - on_delegation: 子代理完成观察                             │  │
│  - on_memory_write: 内置记忆修改镜像（Mirror hook）          │  │
│                                                              │
│  工具接口（2 个）：                                            │
│  - get_tool_schemas: 返回工具定义                            │  │
│  - handle_tool_call: 处理工具调用                            │  │
│                                                              │
│  配置（2 个）：                                                │
│  - get_config_schema: 配置字段定义                           │  │
│  - save_config: 保存配置                                     │  │
└──────────────────────────────────────────────────────────────┘
                          ▲
                          │ 实现
┌──────────────────────────────────────────────────────────────┐
│                  FileMemoryProvider                           │
│                                                              │
│  - MEMORY.md: Agent 持久记忆（用户偏好、环境、工具经验）     │  │
│  - USER.md: 用户画像（角色、背景、习惯）                     │  │
│  - 操作: add/replace/remove 记忆条目                         │  │
│  - 原子写入: 临时文件 + rename 防止并发丢失                  │  │
│  - 字符数限制: memory_char_limit=2200, user_char_limit=1375 │  │
│  - memory 工具: OpenAI 函数调用格式 schema                   │  │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                  Context Fencing                              │
│                                                              │
│  - <memory-context provider="name"> 标签包裹记忆上下文       │  │
│  - [System note: ... NOT new user input ...] 系统注释        │  │
│  - sanitize_context(): 一次性清洗（正则移除标签块）          │  │
│  - StreamingContextScrubber: 流式清洗器（状态机）            │  │
│    - in_span / not_in_span 两个状态                          │  │
│    - buf 缓冲区保留部分标签                                  │  │
│    - flush 时仍在 span 内丢弃（比泄露更安全）                │  │
│    - 块边界检查：只在行首或空白后识别标签                    │  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### 初始化流程
1. `MemoryManager.initialize_all(session_id)` → 调用所有提供者的 `initialize`
2. `FileMemoryProvider.initialize()` → 确保 MEMORY.md/USER.md 存在

### 每轮对话流程
1. **对话前**: `prefetch_all(user_message)` → 调用所有提供者的 `prefetch` → 包裹 `<memory-context>` 标签 → 注入系统提示
2. **对话开始**: `on_turn_start_all(turn, message)` → 通知所有提供者
3. **对话后**: `sync_all(user_content, assistant_content)` → 调用所有提供者的 `sync_turn`
4. **后台预取**: `queue_prefetch_all(user_message)` → 为下一轮排队预取

### 记忆工具调用流程
1. Agent 调用 `memory` 工具（action=add/replace/remove, target=memory/user, content=...）
2. `MemoryManager.handle_tool_call()` → 路由到 FileMemoryProvider
3. FileMemoryProvider 执行操作 → 原子写入（临时文件 + rename）
4. `MemoryManager.on_memory_write_all()` → 通知外部 provider（Mirror hook）

### 会话结束流程
1. `on_session_end_all(messages)` → 通知所有提供者归档记忆
2. `on_pre_compress_all(messages)` → 压缩前提取关键信息
3. `shutdown_all()` → 清理所有提供者连接

## Design Decisions

| Decision | Reason |
|----------|--------|
| **ABC 定义生命周期而非行为** | 17 个方法中只有 4 个是 abstract，其余 13 个有默认空实现，让 provider 只需实现自己关心的部分 |
| **Fan-out 容错** | 每个 provider 独立 try/except，一个失败不影响其他 provider 和主对话流程（graceful degradation） |
| **单外部提供者限制** | 多个外部 provider 的 prefetch 结果可能冲突，tool schema 可能重名，成本线性增长 |
| **Mirror hook (on_memory_write)** | 内置记忆和外部 provider 保持同步，即使"双轨接线"阶段也能减少分歧 |
| **原子写入** | 临时文件 + rename 防止并发写入丢失更新 |
| **字符数限制** | memory_char_limit=2200, user_char_limit=1375 控制注入系统提示的记忆大小 |
| **上下文隔离标签** | `<memory-context>` 标签 + 系统注释防止 Agent 将注入记忆误认为用户输入 |
| **流式清洗状态机** | 处理可能被分割跨 chunk 的标签，flush 时仍在 span 内丢弃（比泄露更安全） |

## Dependencies
- Internal: None（自包含模块）
- External: 无（Python 标准库）

## Configuration Constants
```python
MEMORY_CHAR_LIMIT = 2200   # MEMORY.md 最大字符数
USER_CHAR_LIMIT = 1375     # USER.md 最大字符数
```

## 外部 Provider 生态（预留接口）

| Provider | 方案 | 特色 |
|----------|------|------|
| Honcho | Dialectic 用户建模 | 自动生成用户画像 |
| Hindsight | 时序滑动窗口 | 按时间衰减的记忆 |
| Mem0 | 向量数据库 | Qdrant 后端，语义相似度检索 |
| Holographic | 压缩全息存储 | 高密度对话表示 |
| OpenViking | 语义嵌入 | 嵌入向量驱动 |
| RetainDB | 保留策略 | 可配置保留规则 |
| SuperMemory | 多源聚合 | 聚合多个来源 |
| ByteRover | 替代向量存储 | 轻量级向量存储 |
