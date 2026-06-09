## MODIFIED Requirements

### Requirement: Section-based prompt assembly
PromptAssembler SHALL 扩展为 section 化组装架构。将现有 stable 层拆分为多个 named sections（identity、system_rules、tool_guidance、skills_prompt、model_tips），每个 section 独立缓存。引入 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记稳定段与动态段的分界。

#### Scenario: Stable sections 被缓存
- **WHEN** identity section 内容与上次组装相同
- **THEN** PromptAssembler SHALL 复用缓存的 section 结果

#### Scenario: Dynamic boundary 标记分界
- **WHEN** system prompt 被组装
- **THEN** 稳定 sections SHALL 在 boundary 之前，动态 sections（memory、mcp_instructions、timestamp）在 boundary 之后

### Requirement: Prompt override priority chain
PromptAssembler SHALL 支持 prompt 覆盖优先级链：override > coordinator > agent > custom > default。`append_system_prompt` 始终追加在末尾。

#### Scenario: Custom prompt 替代默认
- **WHEN** 配置了 `customSystemPrompt`
- **THEN** 系统 SHALL 使用 custom prompt 替代默认 system prompt（不是追加）

#### Scenario: Append prompt 始终在末尾
- **WHEN** 配置了 `appendSystemPrompt`
- **THEN** append prompt SHALL 被追加到最终 system prompt 末尾

### Requirement: Prompt observability
PromptAssembler SHALL 支持 prompt 可观测性：dump-prompts 模式将完整 prompt 写入 JSONL 文件，`/context` 命令显示每个 section 的 token 消耗。

#### Scenario: Dump prompts 记录完整交互
- **WHEN** dump-prompts 模式启用
- **THEN** 每次 API 调用的 system prompt 和 messages SHALL 被写入 `~/.nanohermes/dump-prompts/<session-id>.jsonl`
