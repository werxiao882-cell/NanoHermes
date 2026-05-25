# Auxiliary Client Architecture

## Responsibility
为后台任务（压缩、记忆刷写、视觉提取等）提供独立于主对话的 LLM 调用能力。

## Components

```
┌──────────────────────────────────────────┐
│          AuxiliaryClient                  │
│                                          │
│  config: {provider, model, max_tokens}   │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  resolve_config()                  │  │
│  │    ↓                               │  │
│  │  if provider == "main":            │  │
│  │    → use main conversation model  │  │
│  │  else:                             │  │
│  │    → ProviderResolver.resolve()   │  │
│  │    ↓                               │  │
│  │  apply max_tokens default          │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  chat_completion(messages, ...)    │  │
│  │    → delegates to OpenAI/Anthropic │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

## Data Flow
1. 后台任务需要 LLM 调用（如压缩摘要）
2. AuxiliaryClient 解析配置：provider → credentials → client
3. 如果 provider="main"，复用主对话模型的凭证
4. 执行调用，应用 max_tokens 保护
5. 返回结果

## Design Decisions
- **Decision**: 复用 ProviderResolver 而非独立实现凭证逻辑
  - **Reason**: 保持一致性，减少重复代码
- **Decision**: 强制 max_tokens 默认值
  - **Reason**: 防止后台任务消耗过多 token

## Dependencies
- Internal: src/provider (ProviderResolver, OpenAIClient, AnthropicAdapter)
- External: openai SDK, anthropic SDK
