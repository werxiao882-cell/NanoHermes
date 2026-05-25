## ADDED Requirements

### Requirement: 并发限制 SHALL 正确工作
测试 SHALL 验证并发子 Agent 数量限制。

#### Scenario: 并发限制为 3
- **GIVEN** maxConcurrentChildren=3，4 个任务
- **WHEN** 调用 delegateBatch
- **THEN** 前 3 个任务立即启动
- **AND** 第 4 个任务等待直到一个完成

#### Scenario: 深度限制阻止 leaf 委托
- **GIVEN** leaf 角色子 Agent
- **WHEN** 尝试委托
- **THEN** 抛出深度限制错误

#### Scenario: orchestrator 深度限制
- **GIVEN** orchestrator 角色子 Agent，max_spawn_depth=2
- **WHEN** 尝试委托第 3 层
- **THEN** 抛出深度限制错误

### Requirement: 超时处理 SHALL 终止子 Agent
测试 SHALL 验证子 Agent 超时。

#### Scenario: 子 Agent 超时
- **GIVEN** child_timeout_seconds=30
- **WHEN** 子 Agent 运行超过 30 秒
- **THEN** 子 Agent 被终止
- **AND** 返回超时错误
