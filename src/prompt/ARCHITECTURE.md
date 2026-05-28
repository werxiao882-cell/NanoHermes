# Prompt Assembly Architecture

## Responsibility
三层系统提示组装器，确保提示缓存有效。
包含身份、工具指导、技能索引、上下文文件、记忆快照、用户画像等。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    PromptAssembler                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Stable Layer (缓存友好)                                │  │
│  │  - Identity: "你是 NanoHermes..."                      │  │
│  │  - Tool guidance: "你可以使用终端工具..."              │  │
│  │  - Skill hints: available skills list                  │  │
│  │  - Environment hints: working directory, etc.          │  │
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
│  │  - Only rebuild when stable layer changes              │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 初始化时设置 stable 层（身份、工具指导等）
2. 会话开始时设置 context 层（上下文文件等）
3. 每轮对话前设置 volatile 层（记忆快照、用户画像等）
4. 调用 assemble() 组合三层提示
5. 使用 get_stable_hash() 判断是否需要重建缓存

## Design Decisions
- **Decision**: 三层架构分离缓存策略
  - **Reason**: stable 层变化少，适合缓存；volatile 层每轮变化，不缓存
- **Decision**: 使用哈希判断缓存失效
  - **Reason**: 高效判断 stable 层是否变化

## Dependencies
- Internal: src/memory/managers.py (volatile 层记忆注入)
- External: None
