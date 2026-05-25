## ADDED Requirements

### Requirement: Anthropic 缓存控制 SHALL 正确应用
测试 SHALL 验证缓存断点设置。

#### Scenario: 系统提示 + 3 条消息
- **GIVEN** 5 条消息（1 条系统 + 4 条对话）
- **WHEN** 调用 applyAnthropicCacheControl
- **THEN** 系统消息设置 cache_control
- **AND** 最后 3 条非系统消息设置 cache_control
- **AND** 总共 4 个断点

#### Scenario: 少于 4 条消息
- **GIVEN** 3 条消息（1 条系统 + 2 条对话）
- **WHEN** 调用 applyAnthropicCacheControl
- **THEN** 系统消息和 2 条对话消息设置 cache_control

#### Scenario: TTL 设置
- **GIVEN** 消息列表
- **WHEN** 调用 applyAnthropicCacheControl with cacheTtl='1h'
- **THEN** cache_control 标记包含 ttl='1h'
