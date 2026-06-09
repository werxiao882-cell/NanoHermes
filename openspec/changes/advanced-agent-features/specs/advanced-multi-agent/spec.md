## ADDED Requirements

### Requirement: Coordinator mode
系统 SHALL 实现 Coordinator 模式，将主线程改写为调度器。Coordinator 通过 AgentTool 派出 worker，worker 结果以 task-notification 格式回流。工作流显式分相：Research → Synthesis → Implementation → Verification。

#### Scenario: Coordinator 派出多个 worker
- **WHEN** Coordinator 模式下用户请求复杂任务
- **THEN** Coordinator SHALL 分析任务，派出多个 worker subagent 并行执行 research 阶段

#### Scenario: Worker 结果以 task-notification 回流
- **WHEN** worker subagent 完成任务
- **THEN** 结果 SHALL 被包装为 `<task-notification>` XML 格式，作为 user-role message 回流给 Coordinator

### Requirement: Swarm team creation
系统 SHALL 实现 TeamCreateTool，创建包含 team file、task list、leader context 的完整 team 实体。Team file 记录成员列表和元数据。

#### Scenario: 创建 team 实体
- **WHEN** 用户或 agent 调用 TeamCreateTool
- **THEN** 系统 SHALL 创建 team file（JSON）、初始化 task list 目录、设置 leader team context

### Requirement: Teammate mailbox communication
系统 SHALL 实现文件式 Mailbox 通信系统。每个 teammate 有独立的 inbox 文件（JSON），支持并发写入（filelock）。消息类型包括：regular、permission_request、permission_response、shutdown_request、plan_approval。

#### Scenario: Leader 向 teammate 发送消息
- **WHEN** leader 调用 SendMessageTool 指定 teammate 名称
- **THEN** 消息 SHALL 被写入 teammate 的 inbox 文件，带锁保护

#### Scenario: Teammate 轮询 inbox
- **WHEN** teammate 处于空闲状态
- **THEN** 系统 SHALL 周期性轮询 inbox，将未读消息注入 teammate 的执行流

### Requirement: Shared task list collaboration
系统 SHALL 实现共享 task list，team 创建时自动绑定。Teammate 可以 claim 未分配任务、更新任务状态、报告完成结果。

#### Scenario: Teammate 自动 claim 任务
- **WHEN** teammate 空闲且 task list 中有未分配任务
- **THEN** teammate SHALL claim 该任务并更新状态为 in_progress

#### Scenario: 任务完成后通知 leader
- **WHEN** teammate 完成 claimed 任务
- **THEN** 系统 SHALL 更新任务状态为 completed，并通过 mailbox 通知 leader

### Requirement: Leader permission bridge
系统 SHALL 实现 leader 权限桥接，teammate 的权限请求通过 asyncio.Queue 回流到 leader 的 TUI 确认。UI 上显示 worker badge 标识请求来源。

#### Scenario: Teammate 权限请求回流到 leader
- **WHEN** teammate 需要执行需要确认的操作
- **THEN** 权限请求 SHALL 被加入 leader 的确认队列，TUI 显示带 worker badge 的确认对话框

### Requirement: In-process teammate backend
系统 SHALL 实现 in-process teammate 后端，使用 asyncio.Task 隔离上下文。每个 teammate 有独立的 identity、context、abort controller。UI 层将其作为独立 task 展示。

#### Scenario: 多个 teammate 并发运行
- **WHEN** team 中有 3 个 in-process teammate
- **THEN** 系统 SHALL 在同一进程中并发运行 3 个 asyncio.Task，各自维护独立的消息历史和工具上下文

### Requirement: Teammate spawn constraints
系统 SHALL 约束多 Agent 拓扑：teammate 不能嵌套 spawn teammate，in-process teammate 不能启动 background agent。

#### Scenario: Teammate 尝试 spawn teammate 被拒绝
- **WHEN** teammate 调用 AgentTool 指定 team_name
- **THEN** 系统 SHALL 抛出错误 "Teammates cannot spawn other teammates"
