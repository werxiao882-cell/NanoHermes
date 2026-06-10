## ADDED Requirements

### Requirement: Section-based prompt caching
系统 SHALL 将 system prompt 拆分为 named sections，每个 section 独立缓存。使用 SHA256 hash（前 16 位）判断内容是否变化，未变化的 section 复用缓存结果。

#### Scenario: 未变化的 section 复用缓存
- **WHEN** identity section 内容与上次相同
- **THEN** 系统 SHALL 复用缓存的 section 结果，不重新计算

#### Scenario: 变化的 section 重新计算
- **WHEN** memory section 内容因新记忆写入而变化
- **THEN** 系统 SHALL 重新计算该 section 并更新缓存

### Requirement: Dynamic boundary marker
系统 SHALL 在 system prompt 中插入 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记，boundary 之前的 sections 被视为稳定（适合 prompt caching），之后的 sections 允许 session 级变化。

#### Scenario: Boundary 前后分区
- **WHEN** system prompt 包含 identity、system、tools（稳定）和 memory、mcp_instructions（动态）
- **THEN** 稳定 sections SHALL 在 boundary 之前，动态 sections 在 boundary 之后

### Requirement: Prompt override hierarchy
系统 SHALL 实现 prompt 覆盖优先级链：override > coordinator > agent > custom > default。`appendSystemPrompt` 始终追加在末尾。

#### Scenario: Override prompt 完全替代默认
- **WHEN** 提供了 `--system-prompt` 参数
- **THEN** 系统 SHALL 使用 override prompt 替代默认 system prompt

#### Scenario: Agent prompt 在普通模式下替代默认
- **WHEN** 使用 agent 定义且非 proactive 模式
- **THEN** agent system prompt SHALL 替代默认 system prompt（不是追加）

#### Scenario: Append prompt 始终追加在末尾
- **WHEN** 提供了 `--append-system-prompt` 参数
- **THEN** append prompt SHALL 被追加到最终 system prompt 的末尾，无论前面使用哪种覆盖来源

### Requirement: Prompt dump and audit
系统 SHALL 支持 `--dump-prompts` 模式，将 API 请求中的 system prompt、user messages、responses 写入 JSONL 文件（`~/.nanohermes/dump-prompts/<session-id>.jsonl`），供调试和审计。

#### Scenario: Dump prompts 记录完整交互
- **WHEN** `--dump-prompts` 启用
- **THEN** 每次 API 调用的 system prompt、user messages、assistant responses SHALL 被追加写入 JSONL 文件

### Requirement: Section token analysis
系统 SHALL 提供 `/context` 命令，将 effective system prompt 拆成 named entries 并逐段统计 token 消耗，帮助识别最贵的 prompt section。

#### Scenario: 显示每个 section 的 token 数
- **WHEN** 用户执行 `/context` 命令
- **THEN** 系统 SHALL 显示每个 prompt section 的名称和 token 数，按消耗降序排列

### Requirement: Prompt cache invalidation events
系统 SHALL 在特定事件发生时清除 prompt section 缓存：`/clear`、`/compact`、worktree 切换、session resume。

#### Scenario: /compact 清除 prompt 缓存
- **WHEN** 用户执行 `/compact` 命令
- **THEN** 所有 prompt section 缓存 SHALL 被清除，下次请求重新计算
