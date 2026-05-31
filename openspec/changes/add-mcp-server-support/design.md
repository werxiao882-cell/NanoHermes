## Context

NanoHermes 当前是一个自进化 AI Agent 系统，通过 `src/tools/` 模块提供工具能力，但这些工具只能在 NanoHermes 内部对话循环中使用。参考 `msprof_mcp` 的实现，它使用 `mcp` 库的 `FastMCP` 类创建了一个独立的 MCP 服务器，通过 stdio 传输协议暴露工具给外部 LLM 客户端。

当前 NanoHermes 的工具系统包含：
- 工具注册表（`registry.py`）
- 工具分发器（`dispatcher.py`）
- 多种工具实现（terminal、file_tools、memory_tools 等）

需要设计一种机制，将现有工具桥接为 MCP 标准格式。

## Goals / Non-Goals

**Goals:**
- 提供标准 MCP Server 实现，同时支持 3 种传输模式：Stdio（本地必选）、Streamable HTTP（网络主推）、HTTP+SSE（旧版兼容）
- 将 NanoHermes 内部工具桥接为 MCP tools，无需重写工具逻辑
- 支持按需注册 MCP 工具，可配置暴露哪些工具
- 提供 MCP 客户端工具，使 NanoHermes Agent 能通过多种传输方式调用外部 MCP 服务
- 保持与现有工具系统的独立性，不影响内部对话流程

**Non-Goals:**
- 不实现 WebSocket/gRPC/HTTP/2 等自定义传输（规范允许但非标准）
- 不实现 MCP Resources 或 MCP Prompts（仅 Tools）
- 不修改现有 `src/tools/` 模块的内部实现
- 不实现工具的双向同步（MCP ↔ NanoHermes）

## Decisions

### 1. 使用 `mcp` 库的 FastMCP 高层 API

参考 `msprof_mcp` 的实现，使用 `mcp.server.fastmcp.FastMCP` 而非底层 Server API。

**理由：**
- FastMCP 提供装饰器式工具注册，代码更简洁
- `msprof_mcp` 已验证该模式可行
- 底层 API 适合复杂场景，当前需求不需要

**替代方案：**
- 使用 `mcp.server.lowlevel.Server`：更灵活但代码量大，不适合当前场景

### 2. 服务端同时支持 3 种传输模式

根据 MCP 官方规范，服务端需同时支持：

| 传输模式 | 状态 | 使用场景 |
|---------|------|---------|
| **Stdio** | MANDATORY（必选） | 本地进程通信，Claude Desktop/Cherry Studio 集成 |
| **Streamable HTTP** | RECOMMENDED（推荐） | 网络部署，支持会话、断点续传、多客户端并发 |
| **HTTP+SSE** | DEPRECATED（兼容） | 旧版客户端兼容，2025-03 后已弃用 |

实现方式：
```python
# Stdio 模式（默认）
mcp.run(transport="stdio")

# Streamable HTTP 模式
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

# HTTP+SSE 模式（旧版兼容）
mcp.run(transport="sse", host="0.0.0.0", port=8000)
```

通过 `--transport` 命令行参数选择模式，默认 `stdio`。

**理由：**
- Stdio 是本地开发和桌面集成的首选
- Streamable HTTP 是网络部署的标准推荐
- HTTP+SSE 保持对旧版客户端的向后兼容

**替代方案：**
- 仅支持 Stdio：无法满足网络部署需求
- 仅支持 HTTP：无法满足本地桌面集成需求

### 3. MCP 模块独立于现有 tools 模块

新增 `src/mcp/` 目录，包含：
- `server.py` - MCP 服务器入口（参考 `msprof_mcp/server.py`）
- `registry.py` - MCP 工具注册表
- `bridge.py` - 工具桥接逻辑
- `client.py` - MCP 客户端连接管理
- `transports.py` - 传输模式配置和路由

**理由：**
- 保持关注点分离，MCP 是传输层适配
- 不影响现有工具系统的 AST 自动发现机制
- 便于独立测试和部署

### 6. MCP 客户端工具作为标准 NanoHermes 工具

在 `src/tools/` 下新增 `mcp_client_tools.py`，提供以下能力：
- `call_mcp_tool` - 调用外部 MCP 服务的工具
- `list_mcp_tools` - 列出已连接 MCP 服务提供的工具

客户端工具通过 `mcp` 库的 `Client` API 连接外部 MCP 服务，支持 3 种传输方式：

**Stdio 连接：**
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async with stdio_client(StdioServerParameters(command="uvx", args=["some-mcp"])) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("tool-name", arguments={...})
```

**Streamable HTTP 连接：**
```python
from mcp.client.streamable_http import streamablehttp_client

async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("tool-name", arguments={...})
```

**HTTP+SSE 连接（旧版兼容）：**
```python
from mcp.client.sse import sse_client

async with sse_client("http://localhost:8000/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("tool-name", arguments={...})
```

服务配置通过 JSON 文件定义，格式兼容 Cherry Studio / Claude Desktop 标准：
```json
{
  "mcpServers": {
    "msprof-local": {
      "name": "msprof_mcp",
      "description": "msprof mcp server (local)",
      "command": "uvx",
      "args": ["msprof-mcp"],
      "env": {},
      "isActive": true,
      "type": "stdio"
    },
    "msprof-remote": {
      "name": "msprof_mcp_remote",
      "description": "msprof mcp server (remote)",
      "url": "http://remote-server:8000/mcp",
      "isActive": true,
      "type": "streamable-http"
    }
  }
}
```

配置文件路径：`~/.nanohermes/mcp_servers.json`

**字段说明：**
- `type`: 传输类型，可选 `stdio`、`streamable-http`、`sse`
- `command` + `args`: Stdio 模式下的启动命令和参数
- `url`: HTTP 模式下的服务端地址
- `env`: 环境变量字典（Stdio 模式有效）
- `isActive`: 是否启用该服务
- `name` / `description`: 服务元数据（可选）

**理由：**
- 与主流 MCP 客户端（Cherry Studio、Claude Desktop）配置格式一致
- 用户可在不同工具间复用同一份配置
- JSON 格式易于程序解析和验证
- 支持动态连接多个外部 MCP 服务，适配不同部署场景

### 4. 工具桥接采用适配器模式

`bridge.py` 提供 `bridge_tool()` 函数，将 NanoHermes 工具函数包装为 MCP 兼容格式：
- 转换参数 schema（Pydantic → JSON Schema）
- 统一错误处理和返回值格式

**理由：**
- 避免修改现有工具函数签名
- 支持渐进式接入，按需桥接工具

### 5. 日志配置参考 msprof_mcp

- 默认 `WARNING` 级别，避免 stdio 场景污染输出
- 通过环境变量 `NANOHERMES_MCP_LOG_LEVEL` 控制
- 静默 `mcp.server.lowlevel.server` 的 INFO 日志

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| MCP 工具与内部工具参数格式不兼容 | 桥接层统一转换，提供类型校验 |
| 工具数量增加导致 MCP 初始化慢 | 支持懒加载，按需注册工具 |
| stdio 传输模式下日志污染输出 | 默认 WARNING 级别，日志走 stderr |
| `mcp` 库版本升级导致 API 变化 | 锁定 `mcp[cli]>=1.26.0`，定期测试 |
| 外部 MCP 服务连接失败或超时 | 客户端工具实现连接池和超时控制 |
| 多个 MCP 服务工具名称冲突 | 工具调用时指定服务名前缀（如 `service:tool-name`） |
| HTTP 传输模式下并发请求导致资源竞争 | Streamable HTTP 支持会话隔离，限制单会话并发数 |
| HTTP+SSE 旧版协议存在已知限制 | 标记为 DEPRECATED，引导用户迁移到 Streamable HTTP |
