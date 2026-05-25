## ADDED Requirements

### Requirement: InsightsEngine 生成报告 SHALL 正确工作
测试 SHALL 验证完整报告生成。

#### Scenario: 生成完整报告
- **GIVEN** InsightsEngine 实例，有 30 天会话数据
- **WHEN** 调用 generate(30)
- **THEN** 返回包含 overview、models、platforms、tools、skills、activity、topSessions 的报告

#### Scenario: 空数据报告
- **GIVEN** InsightsEngine 实例，无会话数据
- **WHEN** 调用 generate(30)
- **THEN** 返回 empty=true 的报告
- **AND** 所有指标为零

#### Scenario: 按源过滤
- **GIVEN** InsightsEngine 实例，有多个源的会话
- **WHEN** 调用 generate(30, 'cli')
- **THEN** 只包含 cli 源的会话

### Requirement: 终端格式化 SHALL 正确工作
测试 SHALL 验证报告格式化。

#### Scenario: 格式化概览
- **GIVEN** InsightsReport
- **WHEN** 调用 formatTerminal
- **THEN** 包含会话数、消息数、token 数、成本

#### Scenario: 格式化条形图
- **GIVEN** 每日活动数据 [1, 5, 3, 10, 2]
- **WHEN** 调用 formatBarChart
- **THEN** 返回 '█', '█████', '███', '██████████', '██'
