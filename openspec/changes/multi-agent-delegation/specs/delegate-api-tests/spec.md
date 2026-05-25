## ADDED Requirements

### Requirement: delegateTask 函数 SHALL 处理单任务和批量模式
测试 SHALL 验证委托 API。

#### Scenario: 单任务委托
- **GIVEN** delegateTask 函数
- **WHEN** 调用 { goal: 'Analyze this code' }
- **THEN** spawn 一个子 Agent
- **AND** 返回摘要结果

#### Scenario: 批量并行委托
- **GIVEN** delegateTask 函数
- **WHEN** 调用 { tasks: [{ goal: 'Task 1' }, { goal: 'Task 2' }, { goal: 'Task 3' }] }
- **THEN** spawn 多个子 Agent 并行运行
- **AND** 返回所有结果

#### Scenario: 缺少 goal 和 tasks
- **GIVEN** delegateTask 函数
- **WHEN** 调用 {}
- **THEN** 抛出错误 '必须提供 goal 或 tasks'
