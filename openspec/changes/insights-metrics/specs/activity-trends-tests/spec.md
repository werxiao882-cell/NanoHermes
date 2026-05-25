## ADDED Requirements

### Requirement: 活动趋势计算 SHALL 正确工作
测试 SHALL 验证每日活动指标计算。

#### Scenario: 计算每日会话数
- **GIVEN** 30 天的会话数据
- **WHEN** 调用 computeActivityTrend
- **THEN** 返回每天包含会话数、消息数、token 数、成本

#### Scenario: 条形图峰值归一化
- **GIVEN** 每日会话数 [1, 5, 3, 10, 2]
- **WHEN** 调用 formatBarChart with maxWidth=20
- **THEN** 最大值 10 对应 20 个 █，其他按比例

#### Scenario: 全零数据条形图
- **GIVEN** 每日会话数 [0, 0, 0]
- **WHEN** 调用 formatBarChart
- **THEN** 返回空字符串或最小宽度条形图
