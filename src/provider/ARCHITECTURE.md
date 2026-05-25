# Provider Architecture

## Responsibility
统一处理 LLM 提供商交互：凭证解析、API 模式路由、客户端构建、回退链。

## Components

```
┌─────────────────────────────────────────────────────────────┐
│                      Conversation Loop                       │
└────────────┬────────────────────────────────────┬────────────┘
             │                                    │
             ▼                                    ▼
┌────────────────────────┐          ┌────────────────────────┐
│   ProviderResolver     │          │   AuxiliaryClient      │
│                        │          │                        │
│  resolve_credentials() │          │  chat_completion()     │
│  resolve_api_mode()    │          │  (independent routing) │
│  build_client()        │          └────────────────────────┘
└────────┬───────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌─────────┐ ┌──────────────┐
│ OpenAI  │ │  Anthropic   │
│ Client  │ │  Adapter     │
└─────────┘ └──────────────┘
         │
         ▼
┌────────────────────────┐
│   FallbackChain        │
│   (one-shot activate)  │
└────────────────────────┘
```

## Data Flow
1. 调用方传入配置（provider, model, api_mode, fallback_providers）
2. ProviderResolver.resolve() 返回 {provider, api_mode, base_url, api_key, source}
3. 根据 api_mode 选择客户端（OpenAI / Anthropic）
4. 执行 API 调用，提取 usage 和 finish_reason
5. 如果失败且 fallback 配置，激活回退链（一次性）

## Design Decisions
- **Decision**: 使用 openai SDK 作为 chat_completions 基础客户端
  - **Reason**: 支持所有 OpenAI 兼容端点，流式、重试已内置
- **Decision**: api_mode 字符串作为核心路由键
  - **Reason**: 参考 Hermes Agent 架构，所有调用点通过它决定行为
- **Decision**: 纯函数凭证解析，无全局状态
  - **Reason**: 便于测试，支持 profile 隔离

## Dependencies
- Internal: None (基础层)
- External: openai SDK, anthropic SDK
