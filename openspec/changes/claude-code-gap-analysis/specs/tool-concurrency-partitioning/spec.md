## ADDED Requirements

### Requirement: Tool concurrency partitioning

系统 SHALL 实现 `partition_tool_calls()` 函数，将同一轮次的工具调用按 `is_concurrency_safe` 分为并发组和串行组。并发组内工具通过 `asyncio.gather()` 并行执行，串行组工具逐个执行。

#### Scenario: 并发安全工具并行执行

- **WHEN** 模型同时调用 3 个 `is_concurrency_safe=true` 的工具（如 `read_file`, `search_files`, `skill_view`）
- **THEN** 3 个工具通过 `asyncio.gather()` 并行执行
- **AND** 总延迟 ≈ max(单个工具延迟)，而非 sum(所有工具延迟)

#### Scenario: 非并发安全工具串行执行

- **WHEN** 模型同时调用 `terminal`（`is_concurrency_safe=false`）和 `read_file`
- **THEN** 两个工具按声明顺序串行执行
- **AND** 后一个工具等待前一个完成

#### Scenario: 混合调用正确分组

- **WHEN** 同一轮次包含 2 个并发安全工具 + 1 个非并发安全工具 + 2 个并发安全工具
- **THEN** 分为 3 个批次：[并发组1: 2个] → [串行: 1个] → [并发组2: 2个]
- **AND** 批次间严格顺序，批次内并行

#### Scenario: 默认 fail-closed

- **WHEN** 新工具通过 `build_tool()` 创建且未指定 `is_concurrency_safe`
- **THEN** 默认值为 `False`（非并发安全）
- **AND** 该工具只能串行执行

### Requirement: ToolEntry concurrency safety declaration

`ToolEntry` 数据类 SHALL 新增 `is_concurrency_safe: Callable[[dict], bool]` 字段。所有已注册工具必须声明此字段。

#### Scenario: 只读工具声明并发安全

- **WHEN** 工具为 `read_file`, `search_files`, `skill_view`, `skills_list` 等纯读取操作
- **THEN** `is_concurrency_safe` 返回 `True`

#### Scenario: 写操作工具声明非并发安全

- **WHEN** 工具为 `write_file`, `patch`, `terminal` 等写入/执行操作
- **THEN** `is_concurrency_safe` 返回 `False`

### Requirement: dispatch_batch function

系统 SHALL 实现 `dispatch_batch(tool_calls: list[ToolCall]) -> list[ToolResult]` 函数，替代现有 `dispatch()` 的单调用模式。

#### Scenario: 批次执行返回有序结果

- **WHEN** `dispatch_batch()` 被调用，传入 5 个工具调用
- **THEN** 返回 5 个工具结果，顺序与输入一致
- **AND** 每个结果包含 `tool_call_id`, `content`, `status`
