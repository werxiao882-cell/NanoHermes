# Auxiliary Client Architecture

## Responsibility
辅助 LLM 客户端，为后台任务提供独立于主对话的 LLM 调用能力。
支持压缩摘要、记忆刷写、视觉提取、技能审查等后台任务。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    AuxiliaryClient                            │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Configuration                                          │  │
│  │  - provider: "main" or specific provider id            │  │
│  │  - model: model name                                   │  │
│  │  - max_tokens: default 4000                            │  │
│  │  - temperature: optional                               │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Provider Resolution                                    │  │
│  │  - If provider == "main": reuse main conversation      │  │
│  │  - Else: resolve credentials via ProviderResolver      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Client Building                                        │  │
│  │  - OpenAI client for chat_completions                  │  │
│  │  - Anthropic client for anthropic_messages             │  │
│  │  - Lazy initialization (_ensure_client)                │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Chat Completion                                        │  │
│  │  - chat_completion(messages, max_tokens, ...)          │  │
│  │  - Apply max_tokens protection (default 4000)          │  │
│  │  - Support temperature override                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 后台任务需要 LLM 调用（如压缩摘要、记忆审查）
2. AuxiliaryClient 解析配置：provider → credentials → client
3. 如果 provider="main"，复用主对话模型的凭证和 API mode
4. 否则，通过 ProviderResolver 解析独立凭证
5. 构建对应的客户端（OpenAI 或 Anthropic）
6. 执行调用，应用 max_tokens 保护（默认 4000）
7. 返回结果

## Design Decisions
- **Decision**: 复用 ProviderResolver 而非独立实现凭证逻辑
  - **Reason**: 保持一致性，减少重复代码
- **Decision**: 强制 max_tokens 默认值（4000）
  - **Reason**: 防止后台任务消耗过多 token
- **Decision**: 懒加载客户端（_ensure_client）
  - **Reason**: 仅在需要时构建客户端，节省资源

## Dependencies
- Internal: src/provider/ (ProviderResolver, credentials, api_mode)
- External: openai SDK, anthropic SDK
