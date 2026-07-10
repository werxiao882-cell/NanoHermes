# 对话循环模块架构

## 模块概述

核心对话循环引擎，负责模型调用、工具分发、错误分类重试的完整循环。
通过 EventBus 事件驱动架构实现与外部系统（TUI、持久化、调试）的完全解耦。
包含三层系统提示组装器（PromptAssembler），支持 Anthropic prompt caching 和上下文威胁检测。

## 文件职责

```
src/conversation/
├── __init__.py            # 模块入口，导出核心类 + 后台审查向后兼容重导出
├── loop.py                # ConversationLoop：核心对话循环（模型调用→工具分发→重试）
├── events.py              # EventBus + EventType（18 种事件）+ 责任链拦截器机制
├── error_classifier.py    # ErrorClassifier：按 HTTP 状态码分类 API 错误并决策重试
├── debug_handler.py       # DebugHandler：调试输出处理器（仅 debug=True 时注册）
└── assembler.py           # PromptAssembler：三层系统提示组装 + 上下文威胁检测
```

## 核心数据流

```
用户消息 ──→ messages 列表
                │
                ▼
        ┌── ConversationLoop.run() ◄── 迭代上限 max_iterations ──┐
        │                                                         │
        │  emit(ITERATION_START) ──→ 拦截器可修改 messages        │
        │       │                                                 │
        │       ▼                                                 │
        │  emit(MODEL_REQUEST) ──→ 拦截器可阻断/修改请求          │
        │       │                                                 │
        │  blocked? ──Yes──→ 使用 block_message 作为响应          │
        │       │No                                               │
        │       ▼                                                 │
        │  model_call(messages, tools) ──→ response               │
        │       │                                                 │
        │  emit(MODEL_RESPONSE) ──→ 拦截器可修改 response         │
        │       │                                                 │
        │  异常? ──→ ErrorClassifier.classify()                   │
        │       │         ├─ retryable → emit(MODEL_RETRY) → continue
        │       │         └─ 不可重试 → raise                     │
        │       ▼                                                 │
        │  emit(ITERATION_END) ──→ 拦截器可阻断（STOP 语义）      │
        │       │                                                 │
        │  有 tool_calls?                                         │
        │    Yes → emit(TOOL_START) → dispatch → emit(TOOL_END)  │
        │          search_tools? → _process_search_result()       │
        │          追加 tool 消息 → continue ─────────────────────┘
        │    No  → 文本响应 → emit(MESSAGE_APPEND) → return
        │
        └──→ emit(LOOP_END) → background_scheduler.on_loop_end()
```

## 关键设计决策

### EventBus 双层架构（拦截器 + 观察者）
- **为什么**：拦截器（intercept）需要修改数据或阻断流程（如危险命令守卫），观察者（on）只需只读通知（如持久化、日志）
- 拦截器按 priority 升序构成责任链，不调用 `next_fn()` 即阻断；观察者无论是否被阻断都触发，保证持久化不丢失
- `emit()` 返回 `ChainResult(blocked, message)` 供调用方判断

### 动态工具管理（always_loaded + discovered）
- **为什么**：减少每轮发送给模型的 token 数，仅核心工具始终可见，延迟工具通过 `search_tools` 按需发现
- `_discovered_tools` 在 `search_tools` 返回后自动填充，后续轮次合并发送给模型

### PromptAssembler 三层分离
- **为什么**：stable 层（身份/工具/技能）几乎不变，标记为 Anthropic 缓存断点可节省 API 成本；volatile 层（记忆/画像/时间戳）每轮变化，不适合缓存
- 缓存策略：标记最后一个 stable 片段为缓存断点，SHA256 前 16 字符（64 bit）作为缓存失效键

### 上下文威胁检测
- **为什么**：上下文文件（如 AGENTS.md）可能包含提示注入攻击或 API Key 泄露
- 10 种正则模式 + 不可见 Unicode 字符检测，严重程度四级（critical/high/medium/low）

## 对外接口

### 公共类

| 类 | 说明 |
|---|---|
| `ConversationLoop` | 核心循环，`run(messages, tools)` 驱动对话 |
| `EventBus` | 事件总线，`on()`/`off()`/`intercept()`/`emit()` |
| `EventType` | 18 种事件类型枚举 |
| `ChainResult` | emit() 返回值，含 `blocked` 和 `message` |
| `ErrorClassifier` | `classify(status_code, message)` → `ClassifiedError` |
| `ClassifiedError` | 分类结果：`category`, `retryable`, `recovery_hint` |
| `ErrorCategory` | 错误分类枚举（auth/billing/rate_limit 等 8 种） |
| `DebugHandler` | 调试处理器，`register(events)` 订阅全部调试事件 |
| `PromptAssembler` | 三层提示组装器，`build_system_prompt()` → `SystemPromptResult` |
| `SystemPromptResult` | 组装结果：`parts`, `full_text`, `stable_hash`, `threats` |
| `PromptPart` | 提示片段：`content`, `layer`, `cached` |
| `ContextThreat` | 威胁检测结果：`pattern_name`, `severity` |

### ConversationLoop 公共方法

- `run(messages, tools)` → `dict`：运行循环，返回 `{final_response, reasoning, iterations, usage}`
- `interrupt()`：中断循环
- `events`：EventBus 实例，外部通过它订阅事件

### PromptAssembler 公共方法

- `build_system_prompt(model, skills, toolsets, context_files, ...)` → `SystemPromptResult`
- `load_soul_md(path)` → `str`
- `scan_context_content(content)` → `list[ContextThreat]`
- `set_memory_context(data)` / `set_user_profile(profile)`

## 依赖关系

### 依赖其他模块
- `src.background.review`：`__init__.py` 向后兼容重导出（实际代码已迁移）
- `src.skills.progressive_disclosure`：PromptAssembler 内部按需导入，构建技能索引
- `src.memory`：PromptAssembler 通过 `memory_store` 参数注入，读取记忆冻结快照

### 被其他模块依赖
- `src.main`：组合根，创建 ConversationLoop 并注入 `model_call`、`tool_dispatch`
- `src.cli`：TUI 通过 `loop.events.on()` 订阅事件驱动界面更新
- `src.hooks`：通过 `loop.events.intercept()` 注册拦截器（危险命令守卫等）
- `src.session`：通过 `loop.events.on(MESSAGE_APPEND)` 持久化消息
- `src.compression`：通过 `loop.events.on(PRE_COMPRESS)` 触发上下文压缩
