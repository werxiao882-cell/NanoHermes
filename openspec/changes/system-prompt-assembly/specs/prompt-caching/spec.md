## ADDED Requirements

### Requirement: 系统 SHALL 应用 Anthropic 提示缓存策略
系统 SHALL 在系统提示 + 最后 3 条非系统消息上设置 cache_control 断点。所有断点 SHALL 使用相同 TTL（5m 或 1h）。

#### Scenario: 设置缓存断点
- **WHEN** 消息发送给 Anthropic 模型
- **THEN** 系统提示和最后 3 条非系统消息设置 cache_control 标记

#### Scenario: 减少输入 token 成本
- **WHEN** 多轮对话在同一会话中
- **THEN** 缓存命中减少约 75% 的输入 token 成本
