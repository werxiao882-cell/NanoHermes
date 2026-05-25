## ADDED Requirements

### Requirement: 自动拒绝危险命令
测试 SHALL 验证 subagent_auto_approve=false 时的行为。

#### Scenario: 自动拒绝
- **GIVEN** subagent_auto_approve=false
- **WHEN** 子 Agent 运行危险命令
- **THEN** 返回 'deny'
- **AND** 记录警告日志

#### Scenario: 自动批准
- **GIVEN** subagent_auto_approve=true
- **WHEN** 子 Agent 运行危险命令
- **THEN** 返回 'once'
- **AND** 记录警告日志
