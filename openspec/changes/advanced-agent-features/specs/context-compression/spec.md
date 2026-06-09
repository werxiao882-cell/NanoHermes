## MODIFIED Requirements

### Requirement: Multi-strategy compression engine
ContextCompressor SHALL 扩展为多策略压缩引擎。在现有 Summary 压缩基础上，新增 Reactive Compact（PTL 紧急恢复）、Micro Compact（轻量缩减）、Snip Compact（历史裁剪）三种策略。每种策略独立实现，通过策略模式调度。

#### Scenario: 正常流程使用 Auto Compact
- **WHEN** token 使用量超过 auto-compact 阈值
- **THEN** 系统 SHALL 使用现有的 Summary 压缩策略

#### Scenario: PTL 错误触发 Reactive Compact
- **WHEN** API 返回 413 Prompt Too Long 错误
- **THEN** 系统 SHALL 切换到 Reactive Compact 策略进行紧急压缩

### Requirement: Compression circuit breaker integration
ContextCompressor SHALL 集成熔断器。`compress` 方法在调用前检查熔断器状态，连续失败 3 次后跳过压缩。手动压缩成功 SHALL 重置熔断器。

#### Scenario: 熔断器阻止自动压缩
- **WHEN** auto-compact 连续失败 3 次
- **THEN** 后续的 `should_compress` 检查 SHALL 返回 False，跳过压缩

### Requirement: Post-compact message rehydration
ContextCompressor 的 `compress` 方法 SHALL 在返回压缩结果时，同时生成 post-compact messages（包含工具能力声明重建和文件附件恢复）。

#### Scenario: 压缩后重建工具声明
- **WHEN** 压缩完成且系统有 deferred tools
- **THEN** 返回的消息列表 SHALL 包含 deferred tools delta attachment
