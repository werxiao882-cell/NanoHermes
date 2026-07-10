# Provider Runtime 架构文档

## 模块概述

统一的 LLM 提供商运行时，负责凭证解析、API 模式路由、SDK 客户端构建与封装、回退链管理、模型元数据查询。
支持多提供商（OpenAI、Anthropic、OpenRouter、Custom 等），对外提供统一的调用接口，屏蔽不同 SDK 的差异。

## 文件职责

```
src/provider/
├── __init__.py            # 模块公共 API 导出，汇总所有对外符号
├── profile.py             # ProviderProfile 数据类 + ProviderRegistry 全局注册表（含别名解析）
├── builtins.py            # 内置提供商注册：openai、anthropic、openrouter、custom
├── credentials.py         # 凭证解析链（显式 > 环境变量 > 默认），含 Key-Endpoint 隔离检查
├── api_mode.py            # ApiMode 枚举 + 路由解析（显式 > profile > URL 启发式 > 默认）
├── client_factory.py      # SDK 客户端工厂：根据 ApiMode 创建 OpenAI 或 Anthropic 客户端
├── openai_client.py       # OpenAI 客户端封装：流式/非流式/可中断调用、错误分类、TokenUsage
├── anthropic_adapter.py   # Anthropic 适配器：OpenAI ↔ Anthropic 消息和工具格式双向转换
├── fallback.py            # 回退链管理：有序 FallbackEntry 列表，一次性激活防振荡
└── model_metadata.py      # 模型元数据注册表：上下文长度、定价、成本计算
```

## 核心数据流

```
调用方（ConversationLoop / main.py）
    │
    ├─ 1. get_provider_profile(provider_id) ──→ ProviderProfile
    │       └─ resolve_provider_alias("oai") ──→ "openai"
    │
    ├─ 2. resolve_credentials(env_vars, base_url, explicit_key) ──→ CredentialResult
    │       └─ _is_key_compatible() 防止 Key 泄露到错误端点
    │
    ├─ 3. resolve_api_mode(explicit, profile, base_url) ──→ ApiMode
    │       └─ URL 启发式: "api.anthropic.com" → ANTHROPIC_MESSAGES
    │
    ├─ 4. build_client(api_mode, credentials) ──→ OpenAI | Anthropic SDK 实例
    │       ├─ _build_openai_client()     ← chat_completions / codex_responses
    │       └─ _build_anthropic_client()  ← anthropic_messages
    │
    ├─ 5. 封装调用层
    │       ├─ OpenAIClient.build_caller()           ──→ (messages, tools) → dict  [流式闭包]
    │       ├─ OpenAIClient.build_non_stream_caller() ──→ (messages, tools) → dict  [非流式闭包]
    │       ├─ OpenAIClient.interruptible_completion() ──→ 可中断调用（后台线程 + Event）
    │       └─ AnthropicAdapter.chat_completion()     ──→ ChatResponse（格式转换后）
    │
    ├─ 6. 错误处理: classify_error() → ClassifiedError(ErrorCategory, retryable)
    │
    └─ 7. 成本估算: calculate_cost(model_id, tokens) → USD
```

## 关键设计决策

1. **同步 SDK + threading 而非 asyncio**
   - TUI 运行在主线程，SDK 同步版本更稳定；asyncio 需要整个调用链 async，改造成本高
   - `interruptible_completion` 用后台线程 + `threading.Event` 实现跨线程取消信号

2. **build_caller 使用闭包而非类方法**
   - ConversationLoop 期望 `(messages, tools) → dict` 的 callable
   - 闭包捕获 `_client` 和 `_model`，保持接口简洁，无需传递上下文

3. **流式/非流式双模式**
   - `build_caller()` 内部用流式（避免长阻塞、逐步提取 reasoning）
   - `build_non_stream_caller()` 用非流式（子 Agent 只需最终结果，更快更简单）

4. **API Key 隔离机制**
   - `_KEY_ENDPOINT_BINDINGS` 绑定特定 Key 到特定端点，防止 OPENROUTER_API_KEY 泄露到自定义端点

5. **回退链一次性激活**
   - 状态机 IDLE → ACTIVATING → ACTIVATED，激活后不再切换，避免模型间振荡

6. **错误分类基于 HTTP 状态码优先**
   - 状态码标准化程度高于错误消息关键词，分类结果驱动重试策略（retryable 标志）

7. **api_mode 字符串作为核心路由键**
   - 所有分支（客户端选择、格式转换、响应解析）都通过 ApiMode 枚举路由，单一决策点

## 对外接口

其他模块直接使用的公共符号（通过 `__init__.py` 导出）：

| 类型 | 符号 | 用途 |
|------|------|------|
| 数据类 | `ProviderProfile`, `FallbackModel` | 提供商配置描述 |
| 注册表 | `ProviderRegistry` | 全局提供商注册与查找 |
| 函数 | `register_provider()`, `get_provider_profile()` | 注册/获取提供商配置 |
| 函数 | `list_providers()`, `resolve_provider_alias()` | 列出提供商、别名解析 |
| 函数 | `resolve_credentials()` | 凭证解析（返回 CredentialResult） |
| 枚举 | `ApiMode` | API 模式（CHAT_COMPLETIONS / ANTHROPIC_MESSAGES / CODEX_RESPONSES） |
| 函数 | `resolve_api_mode()` | 按优先级解析 API 模式 |
| 函数 | `build_client()` | 工厂函数，创建 SDK 客户端实例 |
| 类 | `FallbackChain`, `FallbackEntry` | 回退链管理 |
| 数据类 | `ModelInfo`, `ModelPricing` | 模型元数据 |
| 函数 | `get_context_length()`, `calculate_cost()` | 模型上下文长度、成本估算 |
| 类 | `OpenAIClient` | OpenAI 客户端封装 |
| 类 | `AnthropicAdapter` | Anthropic 格式适配器 |
| 数据类 | `ChatResponse`, `TokenUsage`, `ClassifiedError`, `ErrorCategory` | 响应/错误封装 |

## 依赖关系

**外部依赖**:
- `openai` SDK — OpenAI 兼容端点的底层客户端
- `anthropic` SDK — Anthropic Messages API 的底层客户端

**内部依赖**:
- 本模块是纯运行时层，不依赖其他 `src/` 模块
- 上游调用方：`src/conversation/loop.py`（通过 `build_client` + `build_caller` 获取模型调用函数）
- 上游调用方：`src/main.py`（组合根，注入 provider 配置和凭证）
- 配置来源：`nanohermes.json` / `.env` 提供 API Key、Base URL、provider 选择
