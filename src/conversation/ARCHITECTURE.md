# Conversation Loop Architecture

## Responsibility
核心对话循环，管理模型调用、工具分发、错误分类、重试、后台审查。
支持 debug 模式、工具回调、消息追加回调。

## 目录结构

```
src/conversation/
├── __init__.py            # 模块入口
├── loop.py                # ConversationLoop 核心循环
├── events.py              # EventBus + EventType（18 种事件）
├── error_classifier.py    # ErrorClassifier 错误分类和重试决策
├── debug_handler.py       # DebugHandler 调试输出（订阅事件总线）
├── background_review.py   # spawn_background_review + fork_agent
└── assembler.py           # PromptAssembler 系统提示组装（三层架构）
```

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    User Input                                 │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   ConversationLoop                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Model Call                                             │  │
│  │  - call_model(messages, tools) → response              │  │
│  │  - Extract content, tool_calls, usage, reasoning       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Tool Dispatch                                          │  │
│  │  - dispatch_tool(name, args) → result                  │  │
│  │  - on_tool_start callback                              │  │
│  │  - on_tool_end callback (with elapsed time)            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Error Handling                                         │  │
│  │  - ErrorClassifier: auth, billing, rate_limit, etc.    │  │
│  │  - Retry on retryable errors                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Message Persistence                                    │  │
│  │  - on_message_append callback → JSONL store            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Background Review                                      │  │
│  │  - spawn_background_review(messages)                   │  │
│  │  - fork_agent with tool whitelist                      │  │
│  │  - Memory/skill review prompts                         │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 用户输入消息添加到 messages 列表
2. 调用 model_caller(messages, tool_schemas)
3. 解析响应：content, tool_calls, usage, reasoning
4. 如果有 tool_calls：
   - 触发 on_tool_start 回调
   - 调用 tool_dispatch(name, args)
   - 触发 on_tool_end 回调（含耗时）
   - 将工具结果添加到 messages
   - 触发 on_message_append 回调（保存到 JSONL）
   - 继续循环
5. 如果没有 tool_calls：
   - 显示最终响应
   - 保存到 SQLite 和 JSONL
   - 同步记忆系统
6. 后台审查线程异步评估对话内容

## EventBus 拦截器机制

emit() 执行流程：拦截器链（责任链递归） → 观察者（原有 handler）

- **拦截器**：intercept(type, handler, priority) 注册，签名 (data, next)→None
  - 调用 next() 放行，不调用 next() 阻断
  - 可修改 data dict，可执行前后置逻辑（洋葱模型）
  - 按 priority 升序执行，异常被捕获跳过
- **观察者**：on(type, handler) 注册（不变），签名 (data)→None
  - 拦截器链完成后触发（无论是否被阻断）
  - 异常被捕获跳过
- **返回值**：emit() 返回 ChainResult(blocked, message)

事件分类：可阻断（3 种）/ 可修改（7 种）/ 仅观察（8 种）

## Design Decisions
- **Decision**: 使用回调机制解耦对话循环和外部系统
  - **Reason**: 对话循环不依赖具体的存储或显示实现
- **Decision**: 工具回调包含耗时信息
  - **Reason**: 方便用户了解工具执行效率
- **Decision**: 后台审查使用工具白名单
  - **Reason**: 防止审查 Agent 执行危险操作

## Dependencies
- Internal: src/provider/, src/tools/core/, src/session/, src/config/
- External: openai SDK

---

# Prompt Assembly Architecture (merged from src/prompt/)

## Responsibility
三层系统提示组装器，确保提示缓存有效。
段落化结构（Claude Code 风格）：Identity → Tool Usage → Skills → Operational Guidance → Context Files → Memory → User Profile → Timestamp。
包含身份、工具指导（含 select: 精确加载语法）、技能索引（含 TRIGGER/SKIP 规则）、上下文文件、记忆快照、用户画像等。

### 安全特性
- **上下文威胁检测**：10 种正则模式检测提示注入攻击和数据泄露风险
- **不可见 Unicode 字符检测**：防止隐藏字符干扰模型理解
- **严重程度分级**：critical（API Key 泄露）、high（系统覆盖）、medium（指令覆盖）、low

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    PromptAssembler                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Stable Layer (缓存友好, 段落化结构)                    │  │
│  │  - # Identity: SOUL.md 内容                            │  │
│  │  - # Tool Usage: Always-Loaded + Deferred (分组)       │  │
│  │    + select:<name> 精确加载语法                        │  │
│  │  - # Skills: TRIGGER/SKIP 内联格式                     │  │
│  │  - # Operational Guidance: 模型特定指导                │  │
│  │  → Changes rarely, good for prompt caching             │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Context Layer                                          │  │
│  │  - Context files: AGENTS.md, .cursorrules, etc.        │  │
│  │  - System message overrides                            │  │
│  │  → Changes per session                                 │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Volatile Layer (每轮变化)                              │  │
│  │  - Memory snapshot: <memory-context>...</memory-context>│  │
│  │  - User profile: preferences, history                  │  │
│  │  - Timestamp: current time                             │  │
│  │  → Changes every turn                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Cache Hash                                             │  │
│  │  - get_stable_hash() for cache invalidation            │  │
│  │  - SHA256 前 16 字符（64 bit），碰撞概率极低           │  │
│  │  - Only rebuild when stable layer changes              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Threat Detection                                       │  │
│  │  - 10 patterns: injection, override, key leak, etc.    │  │
│  │  - Invisible Unicode detection                         │  │
│  │  - Severity: critical/high/medium/low                  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 初始化时设置 stable 层（身份、工具指导等）
2. 会话开始时设置 context 层（上下文文件等）
3. 每轮对话前设置 volatile 层（记忆快照、用户画像等）
4. 调用 assemble() 组合三层提示
5. 使用 get_stable_hash() 判断是否需要重建缓存
6. 扫描上下文内容中的威胁模式

## Design Decisions

### 三层架构分离缓存策略
- **Decision**: stable/context/volatile 三层分离
- **Reason**: 
  - stable 层变化少（身份、工具指导），适合 Anthropic prompt caching
  - context 层每会话变化（上下文文件）
  - volatile 层每轮变化（时间戳、记忆），不适合缓存
  - 缓存最后一个 stable 部分可以缓存所有 stable 内容

### 缓存哈希设计
- **Decision**: 使用 SHA256 前 16 字符（64 bit）
- **Reason**: 
  - SHA256 碰撞概率极低（1/2^64）
  - 64 bit 足够唯一且节省存储空间
  - 用于判断 stable 层内容是否变化，触发缓存失效

### Anthropic 缓存优化
- **Decision**: 标记最后一个 stable 部分为缓存断点
- **Reason**: 
  - Anthropic 要求缓存内容在 prompt 前部
  - stable 层是不变内容，最适合缓存
  - 标记断点可以缓存所有 stable 内容，减少 API 调用成本

### 威胁检测策略
- **Decision**: 使用正则表达式检测 10 种威胁模式
- **Reason**: 
  - 检测提示注入攻击（ignore previous instructions, override system prompt 等）
  - 检测数据泄露风险（curl 命令中的 API Key, api_key= 赋值等）
  - 检测不可见 Unicode 字符（可能用于隐藏信息）
  - 严重程度分级帮助优先处理关键威胁

## Dependencies
- Internal: src/config/ (配置模块), 直接读取 ~/.nanohermes/memory/ 文件（volatile 层记忆注入）
- External: None
