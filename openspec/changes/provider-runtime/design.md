## Context

NanoHermes 从零构建，参考 Hermes Agent 的 provider runtime 架构（Python 实现，~30 个提供商插件）。NanoHermes 使用 TypeScript + Node.js，需要适配 JavaScript 生态的 LLM SDK。

当前项目只有 package.json（依赖 better-sqlite3），无现有 provider 层。

## Goals / Non-Goals

**Goals:**
- 统一的 Provider 接口，上层代码不直接调用 OpenAI/Anthropic SDK
- 支持至少 3 种 API Mode：chat_completions、anthropic_messages、codex_responses
- 凭证从环境变量解析，支持多优先级回退
- 辅助 LLM 客户端独立于主对话路由
- 回退模型链在主模型失败时自动激活

**Non-Goals:**
- 不实现 OAuth 流程（第一阶段只用 API Key）
- 不实现插件式提供商注册（第一阶段内置提供商，插件系统后续添加）
- 不实现模型 catalogs（硬编码常用模型列表即可）
- 不实现 prompt caching 策略（由 prompt-assembly 模块负责）

## Decisions

### 1. 使用 openai SDK 作为唯一 HTTP 客户端

**Decision**: 使用 `openai` npm 包作为所有 API Mode 的基础客户端。

**Why**: openai SDK 支持 chat completions 格式，且可通过 baseURL 和自定义 fetch 适配大多数 OpenAI 兼容端点。Anthropic 模式使用 `@anthropic-ai/sdk`。

**Alternatives considered**:
- 直接用 fetch/axios：需要自己处理流式、重试、错误分类，工作量大
- 用 ai SDK (Vercel)：过度抽象，不利于精细控制

### 2. API Mode 作为核心路由键

**Decision**: api_mode 字符串决定请求格式、客户端类型、响应解析逻辑。

```
chat_completions     → openai.OpenAI 客户端，标准消息格式
anthropic_messages   → Anthropic 客户端，需消息格式转换
codex_responses      → openai.OpenAI 客户端，Responses API 格式
```

**Why**: 参考实现中 api_mode 是统一的路由键，所有调用点（主循环、辅助、回退）都通过它决定行为。

### 3. 凭证解析使用纯函数，不依赖全局状态

**Decision**: resolveCredentials(provider, config) 返回 { apiKey, baseUrl, source }，不读写全局变量。

**Why**: 便于测试，避免 profile 隔离问题。调用方负责传入配置和传递结果。

### 4. 辅助客户端复用相同的 Provider 接口

**Decision**: AuxiliaryClient 内部复用 ProviderResolver，不单独实现凭证逻辑。

**Why**: 辅助任务可能需要不同的提供商（如主对话用 Claude，压缩用 GPT-4o-mini），但凭证解析逻辑相同。

### 5. 回退链一次性激活

**Decision**: fallback_activated 标志防止反复切换。激活后保持新模型直到对话结束。

**Why**: 避免在主模型和回退模型之间振荡。参考实现中这也是标准行为。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| openai SDK 版本升级可能破坏 API | 锁定版本范围 `>=x.y,<x+1` |
| 多个 SDK 实例导致连接池浪费 | 单例模式缓存客户端实例 |
| 凭证泄露到错误端点 | 严格的 baseUrl 匹配检查，不同提供商的 key 不混用 |
| 辅助任务使用昂贵模型 | 配置强制要求辅助模型默认值，无配置时拒绝执行 |
| 回退模型能力不足导致工具调用失败 | 回退链按能力排序，确保回退模型支持工具调用 |

## Open Questions

- 是否需要支持流式响应的 token 计数？（影响成本估算精度）
- Codex Responses API 是否在第一阶段实现？（可推迟到需要时）
