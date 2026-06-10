## ADDED Requirements

### Requirement: Streaming tool execution during model response
系统 SHALL 在模型流式输出期间，检测到完整的 tool_use block 后立即启动工具执行（通过 asyncio.Task），无需等待模型完整响应。

#### Scenario: 工具在流式输出期间提前执行
- **WHEN** 模型流式输出中包含完整的 tool_use block（JSON input 已完整解析）且工具标记为 isConcurrencySafe
- **THEN** 系统 SHALL 立即创建 asyncio.Task 开始执行该工具，不等待模型响应结束

#### Scenario: 非并发安全工具等待完整响应
- **WHEN** 模型流式输出中包含 tool_use block 但工具未标记 isConcurrencySafe
- **THEN** 系统 SHALL 等待模型完整响应后再执行该工具

### Requirement: Streaming execution result collection
系统 SHALL 在模型响应结束后收集所有提前执行的工具结果，按原始顺序排列，与正常执行路径的结果格式一致。

#### Scenario: 收集提前执行的结果
- **WHEN** 模型响应结束且有 3 个工具已提前执行完毕
- **THEN** 系统 SHALL 按 tool_use block 的原始顺序收集结果，格式与串行执行一致

### Requirement: Fallback cancellation
系统 SHALL 在模型回退（fallback）触发时，取消所有 pending 的 streaming tool execution Task，丢弃已执行结果，重新初始化执行器。

#### Scenario: 模型回退取消 pending 工具
- **WHEN** 模型回退被触发（FallbackTriggeredError）
- **THEN** 系统 SHALL 取消所有正在执行的 streaming tool Task，清空结果缓冲区，为 fallback 模型创建新的执行器
