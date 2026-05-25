## ADDED Requirements

### Requirement: 成本估算 SHALL 正确计算
测试 SHALL 验证成本计算逻辑。

#### Scenario: 估算已知模型成本
- **GIVEN** 模型 'gpt-4'，inputTokens=1000, outputTokens=500
- **WHEN** 调用 estimateCost
- **THEN** 返回基于定价的正确 USD 成本

#### Scenario: 估算缓存 token 成本
- **GIVEN** 模型 'claude-3-sonnet'，cacheReadTokens=2000, cacheWriteTokens=1000
- **WHEN** 调用 estimateCost
- **THEN** 返回包含缓存成本的 USD 成本

#### Scenario: 未知模型成本
- **GIVEN** 模型 'unknown-model'
- **WHEN** 调用 estimateCost
- **THEN** 返回 { amountUsd: 0, status: 'unknown' }
