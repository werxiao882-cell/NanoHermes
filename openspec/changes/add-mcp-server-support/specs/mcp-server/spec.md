## ADDED Requirements

### Requirement: MCP Server 创建与配置

系统 SHALL 提供基于 `mcp` 库 FastMCP 的 MCP 服务器实例，支持服务器名称、版本等基础配置。

#### Scenario: 创建默认服务器
- **WHEN** 调用 `create_server()` 且未指定参数
- **THEN** 创建名为 "nanohermes-mcp" 的 FastMCP 实例

#### Scenario: 服务器配置可自定义
- **WHEN** 调用 `create_server(name="custom-name")`
- **THEN** 创建指定名称的 FastMCP 实例

### Requirement: 多传输模式支持

系统 SHALL 支持 3 种 MCP 官方传输模式：Stdio（必选）、Streamable HTTP（推荐）、HTTP+SSE（旧版兼容）。

#### Scenario: 启动 stdio 服务器（默认）
- **WHEN** 调用 `mcp.run(transport="stdio")` 或未指定传输模式
- **THEN** 服务器通过标准输入/输出与客户端通信

#### Scenario: 启动 Streamable HTTP 服务器
- **WHEN** 调用 `mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)`
- **THEN** 服务器在 `http://0.0.0.0:8000/mcp` 监听，支持 HTTP POST 请求和 SSE 流式响应

#### Scenario: 启动 HTTP+SSE 服务器（旧版兼容）
- **WHEN** 调用 `mcp.run(transport="sse", host="0.0.0.0", port=8000)`
- **THEN** 服务器在 `http://0.0.0.0:8000/sse` 监听，支持旧版 SSE 单向流

#### Scenario: 命令行选择传输模式
- **WHEN** 执行 `python -m src.mcp.server --transport streamable-http --port 8000`
- **THEN** 服务器以 Streamable HTTP 模式启动

### Requirement: 日志配置

系统 SHALL 提供日志级别配置，默认使用 WARNING 级别以避免在 stdio 场景下污染输出。

#### Scenario: 默认日志级别
- **WHEN** 未设置环境变量 `NANOHERMES_MCP_LOG_LEVEL`
- **THEN** 日志级别为 WARNING

#### Scenario: 自定义日志级别
- **WHEN** 设置环境变量 `NANOHERMES_MCP_LOG_LEVEL=DEBUG`
- **THEN** 日志级别为 DEBUG，输出详细调试信息

#### Scenario: 静默 MCP 底层日志
- **WHEN** 服务器运行
- **THEN** `mcp.server.lowlevel.server` 的 INFO 日志被抑制为 WARNING

### Requirement: 独立启动入口

系统 SHALL 提供独立的 MCP 服务器启动入口，不依赖 NanoHermes 主对话流程。

#### Scenario: 命令行启动
- **WHEN** 执行 `python -m src.mcp.server`
- **THEN** MCP 服务器启动并监听 stdio
