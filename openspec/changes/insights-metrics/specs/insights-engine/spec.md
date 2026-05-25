## ADDED Requirements

### Requirement: 系统 SHALL 分析会话历史生成洞察
InsightsEngine SHALL 查询会话数据生成完整报告，包含：概览、模型分解、平台分解、工具使用、技能使用、活动趋势、顶部会话。

#### Scenario: 生成洞察报告
- **WHEN** 请求洞察并指定时间范围
- **THEN** 系统返回包含所有部分的报告

#### Scenario: 处理空数据
- **WHEN** 时间范围内无会话
- **THEN** 系统返回空报告，指标为零

### Requirement: 系统 SHALL 从 token 使用估算成本
系统 SHALL 基于 token 计数（input、output、cache read、cache write）和模型定价数据计算 USD 成本估算。

#### Scenario: 估算会话成本
- **WHEN** 会话有 token 计数
- **THEN** 系统使用模型定价数据计算成本

#### Scenario: 处理未知定价
- **WHEN** 模型无已知定价数据
- **THEN** 成本标记为 "unknown"，不计入总计

### Requirement: 系统 SHALL 计算每日活动趋势
系统 SHALL 计算每日活动指标：每日会话数、每日消息数、每日 token 数、每日成本。趋势 SHALL 在终端输出中可视化为条形图。

#### Scenario: 计算每日活动
- **WHEN** 生成活动数据时
- **THEN** 周期内每天包含会话数、消息数、token 数和成本

#### Scenario: 生成条形图可视化
- **WHEN** 格式化终端输出时
- **THEN** 使用 █ 字符生成水平条形图
