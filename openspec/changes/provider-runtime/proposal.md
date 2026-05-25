## Why

NanoHermes 需要与多个 LLM 提供商（OpenAI、Anthropic、OpenRouter 等）交互，每种提供商有不同的 API 格式、认证方式和错误模式。Provider Runtime 层统一处理凭证解析、API 模式路由、客户端构建和回退链，使上层（对话循环、压缩、辅助任务）无需关心底层提供商细节。

## What Changes

- 实现 Provider 抽象接口和注册表，支持插件式扩展
- 实现凭证解析链（环境变量 → 配置文件 → 默认值）
- 实现 API Mode 路由（chat_completions、anthropic_messages、codex_responses）
- 实现 OpenAI 兼容客户端封装，支持流式调用和中断
- 实现辅助 LLM 客户端，用于压缩、记忆刷写等后台任务
- 实现回退模型链，主模型失败时自动切换
- 实现模型元数据管理（上下文长度、定价）

## Capabilities

### New Capabilities

- `provider-interface`: Provider 抽象接口和注册表，支持通过插件注册新提供商。ProviderProfile 包含 api_mode、base_url、env_vars、fallback_models。
- `credential-resolution`: 凭证解析链，按优先级检查环境变量、配置文件、默认值。避免密钥泄露到错误端点。
- `api-mode-routing`: API 模式路由，支持 chat_completions（OpenAI 兼容）、anthropic_messages（原生 Anthropic）、codex_responses（OpenAI Responses API）。模式决定请求格式、客户端类型、响应解析。
- `openai-client`: OpenAI 兼容客户端封装，支持 chat completions 调用、流式响应、中断取消、token 使用量提取。
- `auxiliary-client`: 辅助 LLM 客户端，用于压缩摘要、记忆刷写、视觉提取等后台任务。支持独立于主对话的提供商/模型路由。
- `fallback-chain`: 回退模型链，主模型遇到 429/5xx/401 错误时按配置顺序尝试备用模型。一次性激活，防止反复切换。
- `model-metadata`: 模型元数据管理，包含上下文长度、定价数据。用于 token 预算计算和成本估算。

### Modified Capabilities

<!-- 无现有能力需要修改 -->

## Impact

- 新增 `src/provider/` 目录，包含 Provider 接口、凭证解析、客户端封装
- 新增 `src/auxiliary/` 目录，包含辅助 LLM 客户端
- 所有需要调用 LLM 的模块（conversation-loop、context-compression、memory-system）都依赖此层
- 依赖 openai SDK（npm 包）
- 无破坏性变更，从零开始构建
