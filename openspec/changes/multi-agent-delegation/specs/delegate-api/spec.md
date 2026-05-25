## ADDED Requirements

### Requirement: 系统 SHALL 支持子 Agent 委托
系统 SHALL 提供委托能力，spawn 隔离的子 Agent，包含新鲜对话上下文、受限工具集和独立终端会话。父 Agent 阻塞直到所有子 Agent 完成。

#### Scenario: 单任务委托
- **WHEN** Agent 使用 goal 调用委托
- **THEN** 子 Agent 被 spawn，完成后返回摘要

#### Scenario: 批量并行委托
- **WHEN** Agent 使用 tasks 数组调用委托
- **THEN** 多个子 Agent 并发运行，最多达到 max_concurrent_children 限制

### Requirement: 子 Agent 上下文 SHALL 与父隔离
每个子 Agent SHALL 接收新鲜对话，无父历史。父上下文 SHALL 只看到委托调用和摘要结果，从不看到子 Agent 的中间工具调用或推理。

#### Scenario: 上下文隔离
- **WHEN** 子 Agent 完成任务
- **THEN** 父 Agent 只看到摘要，看不到子 Agent 的工具调用或中间消息
