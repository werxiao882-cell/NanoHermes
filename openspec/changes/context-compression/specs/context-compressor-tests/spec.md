## ADDED Requirements

### Requirement: compress 方法 SHALL 压缩上下文
测试 SHALL 验证头部/尾部保护和摘要生成。

#### Scenario: 压缩长对话
- **GIVEN** ContextCompressor 实例，100 条消息
- **WHEN** 调用 compress
- **THEN** 返回头部消息 + 摘要系统消息 + 尾部消息
- **AND** 头部消息数量正确（前 3 条）
- **AND** 尾部消息在 token 预算内

#### Scenario: 摘要包含正确前缀
- **GIVEN** ContextCompressor 实例
- **WHEN** 调用 compress
- **THEN** 摘要消息包含 '[CONTEXT COMPACTION — REFERENCE ONLY]' 前缀

### Requirement: calculateSummaryBudget 方法 SHALL 按比例计算预算
测试 SHALL 验证预算计算逻辑。

#### Scenario: 小内容预算
- **GIVEN** 压缩内容 10000 字符
- **WHEN** 调用 calculateSummaryBudget
- **THEN** 返回 2000（最小值）

#### Scenario: 中等内容预算
- **GIVEN** 压缩内容 50000 字符
- **WHEN** 调用 calculateSummaryBudget
- **THEN** 返回 2500（50000 * 0.20 / 4）

#### Scenario: 大内容预算上限
- **GIVEN** 压缩内容 500000 字符
- **WHEN** 调用 calculateSummaryBudget
- **THEN** 返回 12000（最大值）

### Requirement: protectHead 方法 SHALL 保护前 N 条消息
测试 SHALL 验证头部保护。

#### Scenario: 保护前 3 条消息
- **GIVEN** 10 条消息
- **WHEN** 调用 protectHead
- **THEN** 返回前 3 条消息

#### Scenario: 消息少于保护数量
- **GIVEN** 2 条消息
- **WHEN** 调用 protectHead
- **THEN** 返回所有 2 条消息

### Requirement: protectTail 方法 SHALL 使用 token 预算保护尾部
测试 SHALL 验证尾部保护。

#### Scenario: 保护尾部消息
- **GIVEN** 10 条消息，contextLength=8000
- **WHEN** 调用 protectTail
- **THEN** 返回尾部消息，总 token 数不超过 2000（8000 * 0.25）
