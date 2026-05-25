## ADDED Requirements

### Requirement: 委托 SHALL 强制执行并发和深度限制
系统 SHALL 限制并发子 Agent 数量为 max_concurrent_children（默认 3），spawn 深度为 max_spawn_depth（默认 2）。child_timeout_seconds 限制 SHALL 终止失控子 Agent。

#### Scenario: 并发限制执行
- **WHEN** 4 个任务被委托，max_concurrent_children=3
- **THEN** 3 个子 Agent 立即启动，第 4 个等待直到一个完成

#### Scenario: 深度限制执行
- **WHEN** leaf 子 Agent 尝试委托
- **THEN** 委托被拒绝，返回深度限制错误

### Requirement: 危险命令审批 SHALL 可配置
子 Agent SHALL 通过 subagent_auto_approve 配置控制危险命令审批。当 false（默认）时，危险命令自动拒绝。当 true 时，自动批准并记录审计日志。

#### Scenario: 自动拒绝危险命令
- **WHEN** subagent_auto_approve 为 false 且子 Agent 运行危险命令
- **THEN** 命令被拒绝，记录警告日志

#### Scenario: 自动批准带审计
- **WHEN** subagent_auto_approve 为 true 且子 Agent 运行危险命令
- **THEN** 命令被批准，记录警告日志用于审计
