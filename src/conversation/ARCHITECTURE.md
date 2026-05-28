# Conversation Loop Architecture

## Responsibility
核心对话循环，管理模型调用、工具分发、错误分类、重试、后台审查。
支持 debug 模式、工具回调、消息追加回调。

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

## Design Decisions
- **Decision**: 使用回调机制解耦对话循环和外部系统
  - **Reason**: 对话循环不依赖具体的存储或显示实现
- **Decision**: 工具回调包含耗时信息
  - **Reason**: 方便用户了解工具执行效率
- **Decision**: 后台审查使用工具白名单
  - **Reason**: 防止审查 Agent 执行危险操作

## Dependencies
- Internal: src/provider/, src/tools/, src/session/, src/memory/
- External: openai SDK
