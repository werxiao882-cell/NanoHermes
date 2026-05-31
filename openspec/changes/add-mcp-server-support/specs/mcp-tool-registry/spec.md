## ADDED Requirements

### Requirement: MCP 工具注册表

系统 SHALL 提供 MCP 工具注册表，用于管理哪些 NanoHermes 工具暴露为 MCP 工具。

#### Scenario: 注册单个工具
- **WHEN** 调用 `register_mcp_tool(name, tool_fn)` 注册一个工具
- **THEN** 该工具被添加到 MCP 工具注册表中

#### Scenario: 批量注册工具
- **WHEN** 调用 `register_mcp_tools(tools_dict)` 批量注册
- **THEN** 所有工具被添加到 MCP 工具注册表中

### Requirement: 工具过滤配置

系统 SHALL 支持通过配置指定哪些工具暴露为 MCP 工具。

#### Scenario: 白名单模式
- **WHEN** 配置 `MCP_TOOLS_INCLUDE=["terminal", "file_read"]`
- **THEN** 仅指定工具被注册为 MCP 工具

#### Scenario: 黑名单模式
- **WHEN** 配置 `MCP_TOOLS_EXCLUDE=["memory_write"]`
- **THEN** 除指定工具外的所有工具被注册为 MCP 工具

### Requirement: 工具元数据映射

系统 SHALL 将 NanoHermes 工具的元数据（名称、描述、参数）映射为 MCP 工具定义。

#### Scenario: 工具名称映射
- **WHEN** 注册工具时
- **THEN** 工具名称转换为 kebab-case 格式（如 `file_read` → `file-read`）

#### Scenario: 工具描述映射
- **WHEN** 注册工具时
- **THEN** 工具的中文描述作为 MCP 工具的 description 字段

### Requirement: 与 FastMCP 集成

系统 SHALL 将注册表中的工具批量注册到 FastMCP 实例。

#### Scenario: 应用注册表到服务器
- **WHEN** 调用 `apply_registry_to_server(mcp, registry)`
- **THEN** 注册表中所有工具通过 `mcp.tool()` 装饰器注册到服务器
