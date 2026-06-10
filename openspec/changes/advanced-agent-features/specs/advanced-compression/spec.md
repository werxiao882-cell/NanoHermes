## ADDED Requirements

### Requirement: Reactive Compact (PTL recovery)
系统 SHALL 实现 Reactive Compact，当 API 返回 Prompt Too Long (413) 错误时，自动触发紧急压缩并重试。最多尝试 1 次，失败后返回错误。

#### Scenario: 413 错误触发紧急压缩
- **WHEN** API 返回 Prompt Too Long 错误
- **THEN** 系统 SHALL 立即触发 Reactive Compact 压缩历史消息，然后用压缩后的消息重试 API 调用

#### Scenario: Reactive Compact 只尝试一次
- **WHEN** Reactive Compact 后重试仍然返回 413 错误
- **THEN** 系统 SHALL 不再重试，返回 Prompt Too Long 错误给用户

### Requirement: Micro Compact
系统 SHALL 实现 Micro Compact，追踪缓存删除的 token 数量，当删除量超过阈值时进行轻量缩减，不需要调用 LLM 生成摘要。

#### Scenario: 缓存删除触发 Micro Compact
- **WHEN** API 响应的 cache_deleted_input_tokens 超过 pending 阈值
- **THEN** 系统 SHALL 标记 Micro Compact boundary，记录释放的 token 数

### Requirement: Snip Compact
系统 SHALL 实现 Snip Compact，对历史消息中的特定片段进行裁剪（而非全量摘要），释放 token 空间。

#### Scenario: 历史片段裁剪
- **WHEN** 历史消息中存在可裁剪的旧 tool_result 块
- **THEN** 系统 SHALL 裁剪这些块并记录释放的 token 数

### Requirement: Compression circuit breaker
系统 SHALL 实现压缩熔断器，当连续 3 次 auto-compact 失败时，完全停止该会话的 auto-compact 请求，防止浪费 API 额度。

#### Scenario: 连续失败触发熔断
- **WHEN** auto-compact 连续失败 3 次
- **THEN** 系统 SHALL 停止后续所有 auto-compact 尝试，直到会话结束或手动 compact 成功

#### Scenario: 手动 compact 成功重置熔断器
- **WHEN** 熔断器已触发但用户手动执行 `/compact` 且成功
- **THEN** 熔断器 SHALL 重置，auto-compact 恢复

### Requirement: Post-compact rehydration
系统 SHALL 在压缩后重建工具能力声明和文件附件上下文，确保模型在压缩后仍知道可用工具和已读取的文件。

#### Scenario: 压缩后重建工具声明
- **WHEN** 压缩完成后
- **THEN** 系统 SHALL 生成 deferred tools delta attachment，重新声明所有工具能力

#### Scenario: 压缩后恢复文件上下文
- **WHEN** 压缩前曾读取过文件
- **THEN** 系统 SHALL 生成 post-compact file attachments，恢复关键文件引用

### Requirement: Auto-compact buffer threshold
系统 SHALL 在上下文达到模型窗口上限前预留 13000 token 缓冲区，提前触发 auto-compact，避免 API 请求因超限被拒绝。

#### Scenario: 缓冲区触发提前压缩
- **WHEN** 当前 token 数 > (有效窗口大小 - 13000)
- **THEN** 系统 SHALL 触发 auto-compact
