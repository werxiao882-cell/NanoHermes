# Memory System Architecture

## Responsibility
插件化记忆系统，支持多种记忆提供者。
通过 MemoryManager 编排器管理记忆提供者生命周期，
将记忆上下文注入系统提示的 volatile 层。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    MemoryProvider (ABC)                       │
│                                                              │
│  Core hooks:                                                 │
│  - initialize(options)                                       │
│  - prefetch(query) → context string                          │
│  - sync_turn(messages)                                       │
│  - shutdown()                                                │
│                                                              │
│  Optional hooks:                                             │
│  - on_turn_start, on_session_end, on_session_switch          │
│  - on_pre_compress, on_delegation, on_memory_write           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    MemoryManager                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Provider Registry                                      │  │
│  │  - Add providers (builtin + external)                  │  │
│  │  - Max 1 external provider enforced                    │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Lifecycle Orchestration                                │  │
│  │  - initialize_all(options)                             │  │
│  │  - prefetch_all(query) → wrapped context               │  │
│  │  - sync_all(messages)                                  │  │
│  │  - shutdown_all()                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Context Fencing                                        │  │
│  │  - Wrap memory context in <memory-context> tags        │  │
│  │  - Prevent model from leaking memory content           │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                 FileMemoryProvider                            │
│                                                              │
│  - MEMORY.md: Agent long-term memory                         │
│  - USER.md: User profile and preferences                     │
│  - Operations: add, replace, remove entries                  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. MemoryManager 初始化时加载所有注册的提供者
2. 每轮对话前调用 prefetch_all() 获取记忆上下文
3. 记忆上下文包裹在 <memory-context> 标签中
4. 注入到系统提示的 volatile 层
5. 每轮对话后调用 sync_all() 同步记忆
6. 会话结束时调用 shutdown_all() 清理资源

## Design Decisions
- **Decision**: 最多允许 1 个外部记忆提供者
  - **Reason**: 防止工具 schema 膨胀，保持系统简洁
- **Decision**: 使用上下文隔离标签
  - **Reason**: 防止模型泄露记忆内容到响应中
- **Decision**: 文件提供者使用 MEMORY.md 和 USER.md
  - **Reason**: 简单持久化，易于用户查看和编辑

## Dependencies
- Internal: src/prompt/assembler.py (volatile 层注入), src/config/ (配置模块)
- External: None
