## ADDED Requirements

### Requirement: Tool result budget

系统 SHALL 实现 `apply_tool_result_budget(result: str, budget: int = 8000) -> str` 函数，对大型工具输出进行 token 级预算控制，防止单个工具结果占满上下文窗口。

#### Scenario: 小结果不截断

- **WHEN** 工具输出 2000 tokens，预算 8000 tokens
- **THEN** 返回完整输出，不做任何截断

#### Scenario: 大结果头尾保留截断

- **WHEN** 工具输出 15000 tokens，预算 8000 tokens
- **THEN** 保留头部 3500 tokens + 尾部 3500 tokens
- **AND** 中间替换为 `\n... [output truncated, ~8000 tokens omitted] ...\n`
- **AND** 返回总长度 ≈ 7000 + 截断标记 ≈ 7100 tokens（在预算内）

#### Scenario: 截断标记包含原始大小

- **WHEN** 工具输出被截断
- **THEN** 截断标记包含原始字节数或 token 数估算
- **AND** 格式: `[output truncated, {N} bytes / ~{M} tokens omitted]`

#### Scenario: 预算可配置

- **WHEN** 配置文件设置 `tool_result_budget: 4000`
- **THEN** 所有工具结果使用 4000 tokens 预算
- **AND** 环境变量 `NANOHERMES_TOOL_RESULT_BUDGET` 优先级高于配置文件

### Requirement: Per-tool override for result budget

特定工具 SHALL 可声明自己的 `max_result_tokens`，覆盖全局预算。

#### Scenario: 终端工具自定义更小预算

- **WHEN** `terminal` 工具声明 `max_result_tokens: 4000`
- **THEN** 即使全局预算为 8000，终端输出也按 4000 截断
- **AND** 理由：终端输出通常更长，需要更严格的控制
