# MCP 模块架构

## 概述

MCP (Model Context Protocol) 模块为 NanoHermes 提供双向 MCP 能力：
1. **MCP Server**: 将 NanoHermes 内部工具暴露给外部 LLM 客户端
2. **MCP Client**: 使 NanoHermes Agent 能够调用外部 MCP 服务提供的工具

## 目录结构

```
src/mcp/
├── __init__.py          # 模块初始化
├── __main__.py          # 启动入口 (python -m src.mcp.server)
├── server.py            # MCP 服务器实现
├── client.py            # MCP 客户端连接管理
├── bridge.py            # 工具桥接层
├── registry.py          # MCP 工具注册表
└── transports.py        # 传输模式配置
```

与 `src/tools/impls/mcp_client_tool.py` 的关系：
mcp_client_tool 提供 Agent 侧接口（call_mcp_tool, list_mcp_tools, register_mcp_service），
封装 mcp/client.py 的调用。

## 传输模式

支持 3 种 MCP 官方传输模式：

| 模式 | 状态 | 使用场景 |
|------|------|---------|
| Stdio | MANDATORY | 本地进程通信，Claude Desktop/Cherry Studio 集成 |
| Streamable HTTP | RECOMMENDED | 网络部署，支持会话、断点续传、多客户端并发 |
| HTTP+SSE | DEPRECATED | 旧版客户端兼容 |

## 关键组件

### 1. 服务器 (server.py)

- `create_server()`: 创建 FastMCP 实例
- `configure_logging()`: 日志配置，避免 stdio 污染
- `main()`: 命令行入口，支持 `--transport` 参数

### 2. 桥接层 (bridge.py)

- `bridge_tool()`: 将 NanoHermes 工具包装为 MCP 兼容格式
- `format_success_response()` / `format_error_response()`: 响应格式化

### 3. 注册表 (registry.py)

- `McpToolRegistry`: 管理工具注册，支持白名单/黑名单
- `to_kebab_case()`: 工具名称转换
- `apply_registry_to_server()`: 批量注册到 FastMCP

### 4. 客户端 (client.py)

- `McpClientManager`: 连接管理器，支持连接池
- `load_service_config()`: 从 JSON 配置文件加载服务

## 配置文件

`~/.nanohermes/mcp_servers.json`:

```json
{
  "mcpServers": {
    "service-name": {
      "type": "stdio",
      "command": "uvx",
      "args": ["some-mcp"],
      "env": {},
      "isActive": true
    }
  }
}
```

## 启动方式

```bash
# Stdio 模式（默认）
python -m src.mcp.server

# Streamable HTTP 模式
python -m src.mcp.server --transport streamable-http --port 8000

# HTTP+SSE 模式
python -m src.mcp.server --transport sse --port 8000
```
