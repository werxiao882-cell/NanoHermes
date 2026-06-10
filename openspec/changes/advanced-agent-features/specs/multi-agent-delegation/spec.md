## MODIFIED Requirements

### Requirement: Three-tier multi-agent system
DelegationManager SHALL 扩展为三层多 Agent 体系。在现有 Leaf/Orchestrator 基础上，新增 Coordinator 模式（主线程改写为调度器）和 Swarm 模式（team + mailbox + task list）。三层共用同一套 query runtime。

#### Scenario: Coordinator 模式派出 worker
- **WHEN** feature flag `coordinator_mode` 启用且用户请求复杂任务
- **THEN** 主线程 SHALL 以 Coordinator 身份运行，通过 AgentTool 派出 worker subagent

#### Scenario: Swarm 模式创建 team
- **WHEN** feature flag `swarm` 启用且调用 TeamCreateTool
- **THEN** 系统 SHALL 创建 team 实体，支持 mailbox 通信和 task list 协作

### Requirement: Agent spawn constraints
DelegationManager SHALL 增加 agent 拓扑约束：teammate 不能嵌套 spawn teammate，in-process teammate 不能启动 background agent，最大嵌套深度保持 max_spawn_depth=2。

#### Scenario: Teammate 嵌套 spawn 被拒绝
- **WHEN** 当前 agent 已是 teammate 且尝试 spawn 新 teammate
- **THEN** 系统 SHALL 抛出错误拒绝操作

### Requirement: Context modifier atomic application
DelegationManager SHALL 在多 agent 并发执行时，收集所有 contextModifier，在批次完成后统一按序应用，防止并发竞争。

#### Scenario: 并发 agent 的 context 修改统一应用
- **WHEN** 3 个并发 agent 各自返回 contextModifier
- **THEN** 系统 SHALL 在批次完成后按 tool_use block 顺序统一应用所有 modifier
