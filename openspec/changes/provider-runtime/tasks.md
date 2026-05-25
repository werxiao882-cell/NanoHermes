## 1. 项目设置

- [ ] 1.1 安装 openai 和 @anthropic-ai/sdk 依赖
- [ ] 1.2 创建 `src/provider/` 目录结构
- [ ] 1.3 创建 `src/auxiliary/` 目录结构
- [ ] 1.4 编写 `src/provider/ARCHITECTURE.md` 架构文档
- [ ] 1.5 编写 `src/auxiliary/ARCHITECTURE.md` 架构文档

## 2. Provider Interface 和注册表

- [ ] 2.1 定义 ProviderProfile 接口（id, name, api_mode, base_url, env_vars, fallback_models）
- [ ] 2.2 实现 PROVIDER_REGISTRY Map 和 registerProvider 函数
- [ ] 2.3 实现 getProviderProfile 和 listProviders 函数
- [ ] 2.4 实现 provider alias 映射和 resolveProviderAlias 函数
- [ ] 2.5 注册内置提供商配置（openai, anthropic, openrouter, custom）
- [ ] 2.6 编写 Provider Registry 单元测试

## 3. 凭证解析

- [ ] 3.1 实现 resolveCredentials 函数，按 env_vars 优先级查找
- [ ] 3.2 实现 base_url 解析（config → profile → env var）
- [ ] 3.3 实现 credential source 追踪
- [ ] 3.4 实现 API Key 隔离检查（key 不发送到错误端点）
- [ ] 3.5 编写凭证解析单元测试

## 4. API Mode 路由

- [ ] 4.1 定义 ApiMode 类型（chat_completions | anthropic_messages | codex_responses）
- [ ] 4.2 实现 resolveApiMode 函数（explicit → profile → heuristic → default）
- [ ] 4.3 实现 base_url 启发式检测（api.anthropic.com → anthropic_messages）
- [ ] 4.4 实现 client type 选择逻辑
- [ ] 4.5 编写 API Mode 路由单元测试

## 5. OpenAI 兼容客户端

- [ ] 5.1 实现 OpenAIClient 类，封装 openai.OpenAI 客户端
- [ ] 5.2 实现 chatCompletion 方法（messages, tools, model, params）
- [ ] 5.3 实现 streamCompletion 方法，支持增量 token yield
- [ ] 5.4 实现 interruptibleCall 方法（后台线程 + 中断事件）
- [ ] 5.5 实现 token usage 提取（input, output, cache_read, cache_write）
- [ ] 5.6 实现错误分类器（auth, rate_limit, context_overflow, billing, server_error）
- [ ] 5.7 编写 OpenAI 客户端单元测试（mock SDK）

## 6. Anthropic 客户端适配

- [ ] 6.1 实现 AnthropicAdapter 类，封装 @anthropic-ai/sdk
- [ ] 6.2 实现消息格式转换（OpenAI → Anthropic 格式）
- [ ] 6.3 实现工具 schema 转换
- [ ] 6.4 实现响应规范化（Anthropic → OpenAI 格式）
- [ ] 6.5 编写 Anthropic 适配器单元测试

## 7. 辅助 LLM 客户端

- [ ] 7.1 实现 AuxiliaryClient 类，复用 ProviderResolver
- [ ] 7.2 实现辅助配置解析（provider, model, max_tokens）
- [ ] 7.3 实现 "main" provider 回退到主对话模型
- [ ] 7.4 实现 max_tokens 默认值保护
- [ ] 7.5 编写辅助客户端单元测试

## 8. 回退模型链

- [ ] 8.1 实现 FallbackChain 类，存储 {provider, model} 列表
- [ ] 8.2 实现 tryFallback 方法，按顺序尝试回退
- [ ] 8.3 实现 one-shot 激活标志（fallback_activated）
- [ ] 8.4 实现回退客户端重建（新凭证 + 新配置）
- [ ] 8.5 编写回退链单元测试

## 9. 模型元数据

- [ ] 9.1 实现 ModelMetadata 注册表（context_length, pricing）
- [ ] 9.2 注册常用模型元数据（Claude, GPT-4, GPT-4o 等）
- [ ] 9.3 实现 getContextLength 查询（未知模型返回默认值）
- [ ] 9.4 实现 calculateCost 函数（基于 token 计数和定价数据）
- [ ] 9.5 编写模型元数据单元测试

## 10. 集成测试

- [ ] 10.1 编写完整调用链集成测试（resolve → create client → call → parse response）
- [ ] 10.2 编写回退链集成测试（主模型失败 → 回退成功）
- [ ] 10.3 编写辅助客户端集成测试（独立配置调用）
- [ ] 10.4 编写中断集成测试（调用中中断 → 干净退出）
