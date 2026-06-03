## 1. 项目结构与依赖

- [x] 1.1 创建 `src/mcp/` 目录及 `__init__.py`
- [x] 1.2 在 `pyproject.toml` 中添加 `mcp[cli]>=1.26.0`、`starlette`、`uvicorn` 依赖
- [x] 1.3 创建 `src/mcp/__main__.py` 支持 `python -m src.mcp.server` 启动
- [x] 1.4 实现 `src/mcp/transports.py` 传输模式配置和路由

## 2. MCP Server 核心实现

- [x] 2.1 实现 `src/mcp/server.py` 中的 `create_server()` 函数，创建 FastMCP 实例
- [x] 2.2 实现 `src/mcp/server.py` 中的 `main()` 函数，支持 `--transport` 参数选择传输模式
- [x] 2.3 实现 Stdio 传输启动逻辑（默认模式）
- [x] 2.4 实现 Streamable HTTP 传输启动逻辑（`--transport streamable-http --host --port`）
- [x] 2.5 实现 HTTP+SSE 传输启动逻辑（`--transport sse --host --port`，旧版兼容）
- [x] 2.6 实现日志配置函数 `configure_logging()`，支持环境变量控制日志级别
- [x] 2.7 验证 3 种传输模式均可正常启动

## 3. 工具桥接层

- [x] 3.1 实现 `src/mcp/bridge.py` 中的 `bridge_tool()` 函数
- [x] 3.2 实现参数 Schema 转换逻辑（Pydantic → JSON Schema）
- [x] 3.3 实现返回值格式化逻辑（成功/错误响应）
- [x] 3.4 编写桥接层单元测试

## 4. MCP 工具注册表

- [x] 4.1 实现 `src/mcp/registry.py` 中的 `McpToolRegistry` 类
- [x] 4.2 实现 `register_mcp_tool()` 和 `register_mcp_tools()` 方法
- [x] 4.3 实现白名单/黑名单过滤配置
- [x] 4.4 实现工具名称 kebab-case 转换
- [x] 4.5 实现 `apply_registry_to_server()` 将注册表应用到 FastMCP 实例
- [x] 4.6 编写注册表单元测试

## 5. MCP 客户端工具实现

- [x] 5.1 实现 `src/mcp/client.py` 中的 `McpClientManager` 类，管理外部服务连接
- [x] 5.2 实现 Stdio 连接逻辑（子进程启动 + stdin/stdout）
- [x] 5.3 实现 Streamable HTTP 连接逻辑（HTTP POST + SSE）
- [x] 5.4 实现 HTTP+SSE 连接逻辑（旧版 SSE 单向流兼容）
- [x] 5.5 实现连接池机制，支持多服务复用
- [x] 5.6 实现 `src/tools/mcp_client_tools.py` 中的 `call_mcp_tool` 工具函数
- [x] 5.7 实现 `list_mcp_tools` 工具函数
- [x] 5.8 实现服务配置加载（`~/.nanohermes/mcp_servers.json`，兼容 Cherry Studio / Claude Desktop 格式）
- [x] 5.8.1 实现 JSON 配置解析器，支持 `stdio`/`streamable-http`/`sse` 类型
- [x] 5.8.2 实现 `isActive` 字段过滤逻辑
- [x] 5.8.3 实现配置文件不存在时的优雅降级
- [x] 5.9 编写客户端工具单元测试

## 6. 工具接入与集成

- [x] 6.1 选择 2-3 个现有工具（如 terminal、file_read）进行桥接试点
- [x] 6.2 在 `server.py` 中集成注册表，注册试点工具
- [x] 6.3 验证 MCP 工具可通过 Stdio 被外部客户端调用
- [x] 6.4 验证 MCP 工具可通过 Streamable HTTP 被外部客户端调用
- [x] 6.5 验证 MCP 工具可通过 HTTP+SSE 被外部客户端调用（旧版兼容）
- [x] 6.6 验证 NanoHermes Agent 可通过 `call_mcp_tool` 调用外部服务（3 种传输方式）

## 7. 配置与文档

- [x] 7.1 添加环境变量配置说明（`NANOHERMES_MCP_LOG_LEVEL`、`MCP_TOOLS_INCLUDE`、`MCP_TOOLS_EXCLUDE`）
- [x] 7.2 更新 `AGENTS.md` 添加 MCP 模块说明
- [x] 7.3 编写 `src/mcp/ARCHITECTURE.md`
- [x] 7.4 编写 MCP 服务配置示例文件（`mcp_servers.example.json`）
- [x] 7.5 编写 JSON 配置字段说明文档

## 8. 测试

- [x] 8.1 编写 MCP Server 集成测试（Stdio 模式）
- [x] 8.2 编写 MCP Server 集成测试（Streamable HTTP 模式）
- [x] 8.3 编写 MCP Server 集成测试（HTTP+SSE 模式）
- [x] 8.4 编写 MCP 客户端工具集成测试（3 种传输方式）
- [x] 8.5 编写 JSON 配置解析器单元测试（含 `isActive` 过滤、类型识别）
- [x] 8.6 编写端到端测试验证 Stdio 通信
- [x] 8.7 编写端到端测试验证 Streamable HTTP 通信
- [x] 8.8 运行 `pytest tests/mcp/ -v` 确保全部通过
