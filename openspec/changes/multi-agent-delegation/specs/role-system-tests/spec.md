## ADDED Requirements

### Requirement: leaf 角色 SHALL 阻止被禁止的工具
测试 SHALL 验证 leaf 角色工具限制。

#### Scenario: leaf 角色阻止 delegate_task
- **GIVEN** leaf 角色子 Agent
- **WHEN** 尝试调用 delegate_task
- **THEN** 调用被阻止，返回拒绝

#### Scenario: leaf 角色阻止 clarify
- **GIVEN** leaf 角色子 Agent
- **WHEN** 尝试调用 clarify
- **THEN** 调用被阻止，返回拒绝

#### Scenario: orchestrator 角色允许 delegate_task
- **GIVEN** orchestrator 角色子 Agent
- **WHEN** 尝试调用 delegate_task
- **THEN** 调用被允许（受深度限制）
