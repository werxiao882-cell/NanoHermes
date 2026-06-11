"""
MCP 服务器入口

支持 3 种传输模式：
- Stdio（默认，本地进程通信）
- Streamable HTTP（网络部署，推荐）
- HTTP+SSE（旧版客户端兼容）
"""

import argparse
import logging
import os
import sys
from mcp.server.fastmcp import FastMCP

from .transports import TransportMode, TransportConfig
from .registry import McpToolRegistry, apply_registry_to_server
from .bridge import bridge_tool_with_schema

logger = logging.getLogger(__name__)

LOG_LEVEL_ENV_VAR = "NANOHERMES_MCP_LOG_LEVEL"
PACKAGE_LOGGER_NAME = "nanohermes.mcp"
DEFAULT_LOG_LEVEL = logging.WARNING
QUIET_LOGGER_NAMES = ("mcp.server.lowlevel.server",)
LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


def _resolve_log_level(level_name: str | None) -> int:
    """解析日志级别"""
    if not level_name:
        return DEFAULT_LOG_LEVEL
    candidate = getattr(logging, level_name.upper(), None)
    return candidate if isinstance(candidate, int) else DEFAULT_LOG_LEVEL


def configure_logging() -> int:
    """配置日志，避免 stdio 场景下污染输出"""
    level = _resolve_log_level(os.getenv(LOG_LEVEL_ENV_VAR))
    package_logger = logging.getLogger(PACKAGE_LOGGER_NAME)
    package_logger.setLevel(level)
    package_logger.propagate = False

    if not any(getattr(handler, "_nanohermes_mcp_handler", False) for handler in package_logger.handlers):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(LOG_FORMAT))
        handler._nanohermes_mcp_handler = True
        package_logger.addHandler(handler)

    for logger_name in QUIET_LOGGER_NAMES:
        logging.getLogger(logger_name).setLevel(max(level, logging.WARNING))

    return level


def create_server(name: str = "nanohermes-mcp") -> FastMCP:
    """创建 FastMCP 服务器实例"""
    mcp = FastMCP(name)
    return mcp


def register_pilot_tools(mcp: FastMCP) -> None:
    """注册试点工具到 MCP 服务器"""
    from src.tools.impls.file_tool import read_file
    from src.tools.impls.terminal import execute_command

    tools_to_register = [
        ("read-file", read_file, {"path": "文件路径", "offset": "起始行号", "limit": "最大行数"}),
        ("execute-command", execute_command, {"command": "要执行的命令", "timeout": "超时时间（秒）"}),
    ]

    for tool_name, tool_fn, param_desc in tools_to_register:
        bridged_name, bridged_fn, schema = bridge_tool_with_schema(tool_fn)
        mcp.tool()(bridged_fn)
        logger.info(f"Registered pilot tool: {bridged_name}")


def run_stdio(mcp: FastMCP) -> None:
    """Stdio 传输启动逻辑"""
    logger.info("Starting MCP server in stdio mode")
    mcp.run(transport="stdio")


def run_streamable_http(mcp: FastMCP, config: TransportConfig) -> None:
    """Streamable HTTP 传输启动逻辑"""
    # 设置 host 和 port 在 settings 中
    mcp.settings.host = config.host
    mcp.settings.port = config.port
    logger.info(f"Starting MCP server in streamable-http mode at {config.get_server_url()}")
    mcp.run(transport="streamable-http")


def run_sse(mcp: FastMCP, config: TransportConfig) -> None:
    """HTTP+SSE 传输启动逻辑（旧版兼容）"""
    # 设置 host 和 port 在 settings 中
    mcp.settings.host = config.host
    mcp.settings.port = config.port
    logger.info(f"Starting MCP server in SSE mode at {config.get_server_url()} (deprecated)")
    mcp.run(transport="sse")


def main():
    """MCP 服务器入口"""
    configure_logging()

    parser = argparse.ArgumentParser(description="NanoHermes MCP Server")
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "streamable-http", "sse"],
        help="传输模式 (默认: stdio)",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="HTTP 监听地址")
    parser.add_argument("--port", type=int, default=8000, help="HTTP 监听端口")
    args = parser.parse_args()

    mcp = create_server()
    register_pilot_tools(mcp)

    registry = McpToolRegistry()
    apply_registry_to_server(mcp, registry)

    config = TransportConfig.from_args(
        transport=args.transport,
        host=args.host,
        port=args.port,
    )

    if config.mode == TransportMode.STDIO:
        run_stdio(mcp)
    elif config.mode == TransportMode.STREAMABLE_HTTP:
        run_streamable_http(mcp, config)
    elif config.mode == TransportMode.SSE:
        run_sse(mcp, config)


if __name__ == "__main__":
    main()
