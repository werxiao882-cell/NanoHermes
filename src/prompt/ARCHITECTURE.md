# Prompt Assembly Architecture

## Responsibility
三层系统提示组装器，确保提示缓存有效。
包含身份、工具指导、技能索引、上下文文件、记忆快照、用户画像等。

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
- Internal: src/memory/managers.py (volatile 层记忆注入), src/config/ (配置模块)
- External: None
