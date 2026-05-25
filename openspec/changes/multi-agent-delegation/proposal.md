## 为什么

业界成熟的自进化 AI Agent 系统支持父 Agent 委托任务给隔离子 Agent，实现并行工作流。子 Agent 拥有独立对话上下文、受限工具集和独立终端会话。NanoHermes 需要实现相同的多 Agent 委托架构。

## 变更内容

- 实现委托 API，支持 goal/tasks 参数
- 实现隔离子 Agent spawn，包含独立上下文
- 实现角色系统：leaf（默认）和 orchestrator
- 实现工具集限制和并发/深度控制
- 实现危险命令审批配置

## 能力

### 新增能力

- `delegate-api`: 委托 API，支持单任务（goal）和批量并行（tasks 数组）模式。父 Agent 阻塞直到所有子 Agent 完成。
- `subagent-spawning`: 隔离子 Agent spawn，包含新鲜对话上下文、受限工具集、独立终端会话。父上下文只看到委托调用和摘要结果。
- `role-system`: 子 Agent 角色系统。leaf 角色（默认）不能访问 delegate_task、clarify、memory、send_message、execute_code。orchestrator 角色保留 delegate_task 能力。
- `concurrency-control`: 并发和深度控制。max_concurrent_children（默认 3）、max_spawn_depth（默认 2）、child_timeout_seconds。
- `approval-config`: 危险命令审批配置。subagent_auto_approve（默认 false）控制自动拒绝或自动批准。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/delegation/` 目录
- 依赖 OpenCode 的 subagent 机制
- 无破坏性变更，从零开始构建
