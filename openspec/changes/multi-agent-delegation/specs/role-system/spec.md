## ADDED Requirements

### Requirement: 子 Agent 角色 SHALL 控制能力
子 Agent SHALL 有两种角色：leaf（默认，专注工作者）和 orchestrator（可 spawn 自己的工作流）。leaf 子 Agent 不能访问 delegate_task、clarify、memory、send_message、execute_code 工具。

#### Scenario: leaf 角色限制
- **WHEN** leaf 子 Agent 尝试调用 delegate_task
- **THEN** 调用被阻止，子 Agent 收到拒绝

#### Scenario: orchestrator 角色能力
- **WHEN** orchestrator 子 Agent 被 spawn
- **THEN** 保留 delegate_task 能力，可 spawn 自己的工作流
