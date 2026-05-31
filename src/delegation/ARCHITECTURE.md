# Multi-Agent Delegation Architecture

## Responsibility
多 Agent 委托管理器，支持父 Agent 委托任务给隔离子 Agent。
支持单任务委托、批量并行委托、角色系统、并发和深度控制。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Parent Agent                               │
│                  delegate_task(goal/tasks)                    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                   DelegationManager                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Task Dispatch                                          │  │
│  │  - Single task: goal string                            │  │
│  │  - Batch tasks: array of {goal, context, toolsets}     │  │
│  │  - Max concurrent: default 3                           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Role System                                            │  │
│  │  - LEAF: worker, cannot delegate                       │  │
│  │  - ORCHESTRATOR: can spawn sub-agents                  │  │
│  │  - Max spawn depth: default 2                          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Sub-Agent Spawn                                        │  │
│  │  - Isolated context                                    │  │
│  │  - Restricted toolsets                                 │  │
│  │  - Timeout protection                                  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Result Collection                                      │  │
│  │  - DelegationResult: task_id, success, summary, error  │  │
│  │  - Parent sees only delegation call + summary          │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. 父 Agent 调用 delegate_task(goal=...) 或 delegate_task(tasks=[...])
2. 检查当前委托深度是否超过 max_depth
3. 单任务模式：spawn 单个子 Agent
4. 批量模式：并行 spawn 多个子 Agent（最多 max_concurrent 个）
5. 子 Agent 在隔离上下文中执行任务
6. 父 Agent 阻塞等待所有子 Agent 完成
7. 收集 DelegationResult 列表返回给父 Agent

## Design Decisions
- **Decision**: 父 Agent 阻塞等待子 Agent 完成
  - **Reason**: 简化控制流，确保结果可用后再继续
- **Decision**: 子 Agent 上下文隔离
  - **Reason**: 防止子 Agent 影响父 Agent 的对话状态
- **Decision**: 角色系统限制 leaf 角色的委托能力
  - **Reason**: 防止无限递归委托

## Dependencies
- Internal: src/tools/ (受限工具集), src/config/ (配置模块)
- External: None
