## Why

NanoHermes 当前通过内部工具系统（`src/tools/`）为 AI Agent 提供能力，但无法作为标准 MCP 服务被外部 LLM 客户端（如 Claude Desktop、Cherry Studio 等）调用。参考 `msprof_mcp` 的实现模式，增加 MCP Server 支持可以让 NanoHermes 的工具能力通过标准协议暴露给更多 AI 应用生态。

## What Changes

- 新增 `src/mcp/` 模块，实现基于 `mcp` 库的 FastMCP 服务器
- 将现有 `src/tools/` 中的部分工具桥接为 MCP tools
- 新增 MCP 服务器入口脚本，同时支持 3 种传输模式：**Stdio**（本地）、**Streamable HTTP**（网络主推）、**HTTP+SSE**（旧版兼容）
- 新增 MCP 客户端工具，使 NanoHermes Agent 能够通过多种传输方式调用外部 MCP 服务
- 添加 `mcp[cli]>=1.26.0` 和 `starlette`、`uvicorn` 依赖（HTTP 传输需要）
- 提供配置方式，支持按需注册 MCP 工具和配置外部 MCP 服务连接

## Capabilities

### New Capabilities

- `mcp-server`: MCP 服务器核心能力，包括 FastMCP 实例创建、日志配置、3 种传输模式支持（Stdio/Streamable HTTP/HTTP+SSE）
- `mcp-tool-bridge`: 将 NanoHermes 内部工具桥接为 MCP 工具的机制
- `mcp-tool-registry`: MCP 工具注册表，管理哪些内部工具暴露为 MCP 工具
- `mcp-client-tool`: MCP 客户端工具，使 NanoHermes Agent 能够通过 Stdio/Streamable HTTP/HTTP+SSE 调用外部 MCP 服务提供的工具

### Modified Capabilities

<!-- 无现有能力需求变更 -->

## Impact

- 新增依赖：`mcp[cli]>=1.26.0`、`starlette`、`uvicorn`（HTTP 传输需要）
- 新增模块：`src/mcp/`（server.py, registry.py, bridge.py, client.py, transports.py 等）
- 新增工具：`src/tools/mcp_client_tools.py`（MCP 客户端工具）
- 不影响现有 `src/tools/` 模块和内部对话流程
- 新增启动入口：`python -m src.mcp.server`（支持 `--transport` 参数选择传输模式）
- 新增 HTTP 端点：`/mcp`（Streamable HTTP）和 `/sse`（HTTP+SSE 兼容）
