## ADDED Requirements

### Requirement: MCP 客户端连接管理

系统 SHALL 提供 MCP 客户端连接管理器，支持通过 3 种传输协议连接外部 MCP 服务：Stdio、Streamable HTTP、HTTP+SSE。

#### Scenario: 通过 Stdio 连接外部 MCP 服务
- **WHEN** 调用 `connect_mcp_service(transport="stdio", command="uvx", args=["some-mcp"])`
- **THEN** 启动子进程并建立 stdio 连接，返回会话对象

#### Scenario: 通过 Streamable HTTP 连接外部 MCP 服务
- **WHEN** 调用 `connect_mcp_service(transport="streamable-http", url="http://localhost:8000/mcp")`
- **THEN** 建立 HTTP POST + SSE 连接，返回会话对象

#### Scenario: 通过 HTTP+SSE 连接外部 MCP 服务（旧版兼容）
- **WHEN** 调用 `connect_mcp_service(transport="sse", url="http://localhost:8000/sse")`
- **THEN** 建立 SSE 单向流连接，返回会话对象

#### Scenario: 连接超时处理
- **WHEN** 外部 MCP 服务在 30 秒内未响应
- **THEN** 抛出超时异常并关闭连接

#### Scenario: 连接池管理
- **WHEN** 多次调用同一 MCP 服务
- **THEN** 复用已有连接而非重复建立新连接

### Requirement: 调用外部 MCP 工具

系统 SHALL 提供工具函数，使 NanoHermes Agent 能够调用外部 MCP 服务提供的工具。

#### Scenario: 调用外部工具成功
- **WHEN** Agent 调用 `call_mcp_tool(service="msprof", tool="analyze_kernel_details", arguments={...})`
- **THEN** 返回外部工具的执行结果

#### Scenario: 外部工具执行失败
- **WHEN** 外部工具抛出异常
- **THEN** 返回包含错误描述的响应，不中断 Agent 执行流程

#### Scenario: 服务未连接
- **WHEN** 调用未连接的 MCP 服务
- **THEN** 返回错误提示，告知 Agent 需要先连接该服务

### Requirement: 列出外部 MCP 工具

系统 SHALL 提供工具函数，列出已连接 MCP 服务提供的所有工具。

#### Scenario: 列出单个服务的工具
- **WHEN** Agent 调用 `list_mcp_tools(service="msprof")`
- **THEN** 返回该服务提供的所有工具名称和描述

#### Scenario: 列出所有服务的工具
- **WHEN** Agent 调用 `list_mcp_tools()` 且未指定服务
- **THEN** 返回所有已连接服务的工具列表

### Requirement: MCP 服务 JSON 配置

系统 SHALL 支持通过 JSON 配置文件定义外部 MCP 服务连接参数，格式兼容 Cherry Studio / Claude Desktop 标准。

#### Scenario: 从 JSON 配置文件加载服务
- **WHEN** 在 `~/.nanohermes/mcp_servers.json` 中定义服务配置
- **THEN** 启动时自动解析 JSON 并加载可用服务列表到连接池

#### Scenario: 解析 Stdio 类型服务配置
- **WHEN** JSON 中包含 `"type": "stdio"` 的服务配置（含 `command`、`args`、`env` 字段）
- **THEN** 正确解析并可通过子进程方式启动该服务

#### Scenario: 解析 HTTP 类型服务配置
- **WHEN** JSON 中包含 `"type": "streamable-http"` 或 `"type": "sse"` 的服务配置（含 `url` 字段）
- **THEN** 正确解析并可通过 HTTP 方式连接该服务

#### Scenario: 支持 isActive 字段控制
- **WHEN** 服务配置中 `"isActive": false`
- **THEN** 该服务不被加载到连接池

#### Scenario: 动态添加服务
- **WHEN** Agent 调用 `register_mcp_service(name, config_dict)`
- **THEN** 新服务被添加到连接池，立即可用

#### Scenario: 配置文件不存在时优雅降级
- **WHEN** `~/.nanohermes/mcp_servers.json` 文件不存在
- **THEN** 系统正常启动，仅记录警告日志，不加载任何外部服务
