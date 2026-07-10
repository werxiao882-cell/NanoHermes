# MCP 模块架构

## 模块概述

MCP (Model Context Protocol) 模块为 NanoHermes 提供双向 MCP 能力：
1. **MCP Server**：将内部工具暴露为 MCP 工具，供外部 LLM 客户端（如 Claude Desktop）调用
2. **MCP Client**：使 Agent 能够连接并调用外部 MCP 服务提供的工具

支持 3 种传输模式：Stdio（本地默认）、Streamable HTTP（网络推荐）、HTTP+SSE（旧版兼容）。

## 文件职责

```
src/mcp/
├── __init__.py          # 模块包声明
├── __main__.py          # python -m src.mcp.server 入口，调用 server.main()
├── server.py            # MCP 服务器：创建 FastMCP 实例、注册试点工具、日志隔离、按传输模式启动
├── client.py            # MCP 客户端管理器：会话池复用、三种传输连接、工具调用/列举、配置加载
├── bridge.py            # 工具桥接层：函数 → MCP 格式（Schema 推导 + 统一返回值包装）
├── registry.py          # 工具注册表：白名单/黑名单过滤、kebab-case 命名转换、批量应用到 FastMCP
├── transports.py        # TransportMode 枚举（str 基类）和 TransportConfig 数据类
└── servers/             # 内置 MCP 服务器（实验性骨架，所有 __init__.py 为空）
    └── msprof_mcp/      # 性能分析服务器（tools/trace_view, resources/perfetto）
```

与 `src/tools/impls/mcp_client_tool.py` 的关系：该工具封装 `McpClientManager`，
提供 Agent 可调用的 `call_mcp_tool`、`list_mcp_tools`、`register_mcp_service` 接口。

## 核心数据流

```
┌──────────────── MCP Server 方向 ────────────────┐
│                                                  │
│  NanoHermes 工具函数 (read_file, execute_command)│
│        │                                         │
│        ▼                                         │
│  bridge_tool_with_schema()                       │
│    ├─ 有 Pydantic model → model_json_schema()    │
│    └─ 无 model → inspect.signature() 推导        │
│        │                                         │
│        ▼  (tool_name, wrapped_fn, schema)        │
│                                                  │
│  McpToolRegistry (include/exclude 过滤)          │
│        │                                         │
│        ▼                                         │
│  apply_registry_to_server() → FastMCP.tool()     │
│        │                                         │
│        ▼                                         │
│  main() 按 TransportMode 启动服务器               │
│    stdio / streamable-http / sse                 │
└──────────────────────────────────────────────────┘

┌──────────────── MCP Client 方向 ────────────────┐
│                                                  │
│  ~/.nanohermes/mcp_servers.json                  │
│        │                                         │
│        ▼                                         │
│  load_service_config() → List[McpServiceConfig]  │
│        │                                         │
│        ▼                                         │
│  McpClientManager.connect_service(config)        │
│    ├─ stdio → StdioServerParameters + stdio_client│
│    ├─ streamable-http → streamablehttp_client    │
│    └─ sse → sse_client                           │
│        │                                         │
│        ▼                                         │
│  ClientSession 缓存到 _sessions[name]            │
│        │                                         │
│        ▼                                         │
│  call_tool() / list_tools() → MCP 结果           │
└──────────────────────────────────────────────────┘
```

## 关键设计决策

1. **日志隔离到 stderr**：`configure_logging()` 将 `nanohermes.mcp` logger 输出到 stderr 并设 `propagate=False`，
   避免 stdio 传输模式下日志污染 JSON-RPC 通信。级别通过 `NANOHERMES_MCP_LOG_LEVEL` 环境变量控制，
   默认 WARNING。同时压低 `mcp.server.lowlevel.server` 等第三方 logger 级别。

2. **试点工具硬编码**：`register_pilot_tools()` 直接注册 `read_file` 和 `execute_command` 两个工具
   作为最小可用暴露集。`McpToolRegistry` 的 include/exclude 机制为后续全量暴露预留扩展点。

3. **桥接层 Schema 双路径推导**：`bridge_tool_with_schema()` 优先使用显式 Pydantic model，
   否则通过 `inspect.signature()` 从函数注解推导 JSON Schema（支持 int/float/bool/str），
   降低新工具注册的样板代码。返回值统一包装为 `{"content": [...], "isError": bool}` 格式。

4. **会话池复用**：`McpClientManager._sessions` 字典缓存 `ClientSession`，
   重复调用 `connect_*()` 直接返回已有会话，避免重复握手。`_contexts` 保存底层传输上下文用于断开连接。

5. **TransportMode 使用 str 基类枚举**：值可直接与 argparse `choices` 匹配，
   无需额外转换。`TransportConfig.from_args()` 工厂方法统一从命令行参数构建配置。

6. **延迟导入网络传输依赖**：`connect_streamable_http()` 和 `connect_sse()` 内部 try-import
   `mcp.client.streamable_http` / `mcp.client.sse`，仅在需要时才要求 `mcp[cli]` 依赖。

## 对外接口

### 公共类/函数

| 接口 | 来源 | 用途 |
|------|------|------|
| `McpClientManager` | client.py | 连接管理、工具调用/列举、会话池 |
| `McpServiceConfig` | client.py | 服务配置数据类 |
| `load_service_config()` | client.py | 从 JSON 文件加载服务配置 |
| `McpToolRegistry` | registry.py | 工具注册表（include/exclude 过滤） |
| `apply_registry_to_server()` | registry.py | 批量注册到 FastMCP 实例 |
| `bridge_tool_with_schema()` | bridge.py | 工具函数 → MCP 格式桥接 |
| `format_success_response()` / `format_error_response()` | bridge.py | MCP 标准响应格式化 |
| `TransportMode` / `TransportConfig` | transports.py | 传输模式枚举和配置 |
| `main()` | server.py | MCP 服务器启动入口 |
| `create_server()` | server.py | 创建 FastMCP 实例 |

### 对外依赖

| 依赖 | 用途 |
|------|------|
| `src.tools.impls.file_tool.read_file` | 试点工具：文件读取 |
| `src.tools.impls.terminal.execute_command` | 试点工具：命令执行 |
| `mcp` (第三方) | FastMCP、ClientSession、传输客户端 |

## 配置文件

`~/.nanohermes/mcp_servers.json`：

```json
{
  "mcpServers": {
    "service-name": {
      "type": "stdio",
      "command": "uvx",
      "args": ["some-mcp"],
      "env": {},
      "url": null,
      "isActive": true
    }
  }
}
```

## 启动方式

```bash
python -m src.mcp.server                                          # Stdio（默认）
python -m src.mcp.server --transport streamable-http --port 8000  # Streamable HTTP
python -m src.mcp.server --transport sse --port 8000              # HTTP+SSE（旧版）
```
