# Provider Runtime Architecture

## Responsibility
统一的 LLM 提供商运行时，处理凭证解析、API 模式路由、客户端构建、回退链。
支持多提供商（OpenAI, Anthropic, OpenRouter, Custom 等）。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Provider Registry                          │
│                                                              │
│  - ProviderProfile: id, name, api_mode, base_url, env_vars  │
│  - register_provider(), get_provider_profile()              │
│  - Built-in providers: openai, anthropic, openrouter, custom│
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Credential Resolution                      │
│                                                              │
│  Priority chain:                                             │
│  1. explicit_key (highest)                                   │
│  2. environment variables (by priority order)                │
│  3. config file values                                       │
│  4. provider defaults                                        │
│                                                              │
│  Security: API key isolation (key → endpoint binding)        │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    API Mode Routing                           │
│                                                              │
│  Priority chain:                                             │
│  1. explicit api_mode argument                               │
│  2. provider profile api_mode                                │
│  3. base_url heuristic (e.g., api.anthropic.com)             │
│  4. default: chat_completions                                │
│                                                              │
│  Supported modes:                                            │
│  - chat_completions: OpenAI-compatible endpoints             │
│  - anthropic_messages: Native Anthropic Messages API         │
│  - codex_responses: OpenAI Responses API (Codex)             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Client Factory                             │
│                                                              │
│  - build_client(api_mode, credentials) → OpenAI/Anthropic   │
│  - OpenAIClient: chat_completion, stream_completion          │
│  - AnthropicAdapter: message format conversion               │
│  - Error classification: auth, billing, rate_limit, etc.     │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Fallback Chain                             │
│                                                              │
│  - FallbackChain: ordered list of {provider, model} pairs   │
│  - One-shot activation (prevent oscillation)                 │
│  - Triggered on: 401/403, 429 after retries, 5xx errors     │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    Model Metadata                             │
│                                                              │
│  - Context length registry (per model)                       │
│  - Pricing data (input/output/cache per 1M tokens)           │
│  - Cost calculation: tokens × pricing                        │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 调用方传入配置（provider, model, api_mode, fallback_providers）
2. ProviderResolver.resolve() 返回 {provider, api_mode, base_url, api_key, source}
3. 根据 api_mode 选择客户端（OpenAI / Anthropic）
4. 执行 API 调用，提取 usage 和 finish_reason
5. 如果失败且 fallback 配置，激活回退链（一次性）
6. 使用 ModelMetadata 计算 token 成本

## Design Decisions
- **Decision**: 使用 openai SDK 作为 chat_completions 基础客户端
  - **Reason**: 支持所有 OpenAI 兼容端点，流式、重试已内置
- **Decision**: api_mode 字符串作为核心路由键
  - **Reason**: 参考 Hermes Agent 架构，所有调用点通过它决定行为
- **Decision**: 纯函数凭证解析，无全局状态
  - **Reason**: 便于测试，支持 profile 隔离
- **Decision**: 回退链一次性激活
  - **Reason**: 避免在主模型和回退模型之间振荡

## Dependencies
- Internal: src/config/ (配置模块提供 API Key 和 Base URL)
- External: openai SDK, anthropic SDK
