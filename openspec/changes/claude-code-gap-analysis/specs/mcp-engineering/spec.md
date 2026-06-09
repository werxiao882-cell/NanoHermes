## ADDED Requirements

### Requirement: MCP timeout control

MCP 客户端 SHALL 使用自定义 `setTimeout` 实现超时控制，而非 `AbortSignal.timeout()`，以规避 Bun/Node 内存泄漏问题。

#### Scenario: 工具调用超时

- **WHEN** MCP 工具调用超过配置的超时时间（默认 30s）
- **THEN** 返回错误: `MCP tool call timed out after {N}s`
- **AND** 连接保持可用，不泄漏资源

### Requirement: MCP description truncation

MCP 工具描述 SHALL 截断至 `MAX_MCP_DESCRIPTION_LENGTH = 2048` 字符，防止过长描述占满 LLM 上下文。

#### Scenario: 长描述被截断

- **WHEN** MCP 服务器返回 5000 字符的工具描述
- **THEN** 截断至 2048 字符
- **AND** 末尾添加 `... (truncated)` 标记

### Requirement: MCP concurrency control

MCP 客户端 SHALL 实施并发连接数限制：本地进程 3 个并发，远程连接 20 个并发。

#### Scenario: 本地并发限流

- **WHEN** 4 个本地 MCP 工具同时被调用
- **THEN** 前 3 个并行执行，第 4 个等待
- **AND** 任一完成后，等待的工具开始执行

### Requirement: MCP auth avalanche protection

MCP 客户端 SHALL 实现 15 分钟 Auth Cache，认证失败一次后短路后续请求，防止认证雪崩。

#### Scenario: 认证失败短路

- **WHEN** MCP 服务器认证失败（401/403）
- **THEN** 缓存失败状态 15 分钟
- **AND** 后续请求直接返回缓存的错误，不尝试重新认证
- **AND** 15 分钟后自动重试

### Requirement: MCP session reconnect

MCP 客户端 SHALL 检测 HTTP 404 和 JSON-RPC -32001 错误，自动重连会话。

#### Scenario: 会话过期自动重连

- **WHEN** MCP 服务器返回 HTTP 404 或 JSON-RPC -32001 (Session expired)
- **THEN** 自动重新建立连接
- **THEN** 重试失败的请求
- **AND** 最多重试 3 次
