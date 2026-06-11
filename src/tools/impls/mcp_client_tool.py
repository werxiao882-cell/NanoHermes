"""
MCP 客户端工具

提供 NanoHermes Agent 调用外部 MCP 服务的工具函数。
- call_mcp_tool: 调用外部 MCP 服务的工具
- list_mcp_tools: 列出已连接 MCP 服务提供的工具
- register_mcp_service: 动态注册外部 MCP 服务
"""

import logging
from typing import Any, Dict, Optional

from ..mcp.client import McpClientManager, McpServiceConfig, load_service_config

logger = logging.getLogger(__name__)

_global_manager: Optional[McpClientManager] = None


def get_manager() -> McpClientManager:
    """获取全局客户端管理器"""
    global _global_manager
    if _global_manager is None:
        _global_manager = McpClientManager()
    return _global_manager


async def call_mcp_tool(
    service: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> str:
    """
    调用外部 MCP 服务的工具

    Args:
        service: MCP 服务名称
        tool: 工具名称
        arguments: 工具参数

    Returns:
        工具执行结果
    """
    manager = get_manager()

    if service not in manager._sessions:
        services = load_service_config()
        for svc in services:
            if svc.name == service:
                await manager.connect_service(svc)
                break
        else:
            return f"Error: Service '{service}' is not connected. Register it first using register_mcp_service()."

    try:
        result = await manager.call_tool(service, tool, arguments)
        content_parts = []
        for content in result.content:
            if hasattr(content, "text"):
                content_parts.append(content.text)
        return "\n".join(content_parts) if content_parts else str(result)
    except Exception as e:
        logger.error(f"Failed to call tool {tool} on service {service}: {e}", exc_info=True)
        return f"Error calling tool '{tool}' on service '{service}': {str(e)}"


async def list_mcp_tools(service: Optional[str] = None) -> str:
    """
    列出已连接 MCP 服务提供的工具

    Args:
        service: 可选，指定服务名称。不指定则列出所有服务的工具。

    Returns:
        工具列表的文本描述
    """
    manager = get_manager()

    if not manager._sessions:
        services = load_service_config()
        for svc in services:
            try:
                await manager.connect_service(svc)
            except Exception as e:
                logger.warning(f"Failed to connect to {svc.name}: {e}")

    if not manager._sessions:
        return "No MCP services are connected. Register a service first."

    try:
        tools = await manager.list_tools(service)
        output = []
        for svc_name, svc_tools in tools.items():
            output.append(f"\nService: {svc_name}")
            if svc_tools:
                for t in svc_tools:
                    output.append(f"  - {t.get('name', 'unknown')}: {t.get('description', 'No description')}")
            else:
                output.append("  (no tools available)")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Failed to list tools: {e}", exc_info=True)
        return f"Error listing tools: {str(e)}"


async def register_mcp_service(
    name: str,
    transport: str = "stdio",
    command: Optional[str] = None,
    args: Optional[list] = None,
    url: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> str:
    """
    动态注册并连接外部 MCP 服务

    Args:
        name: 服务名称
        transport: 传输类型 (stdio/streamable-http/sse)
        command: Stdio 模式的启动命令
        args: Stdio 模式的参数
        url: HTTP 模式的服务地址
        env: 环境变量

    Returns:
        注册结果
    """
    manager = get_manager()

    config = McpServiceConfig(
        name=name,
        transport=transport,
        command=command,
        args=args,
        url=url,
        env=env,
    )

    try:
        await manager.connect_service(config)
        tools = await manager.list_tools(name)
        tool_count = len(tools.get(name, []))
        return f"Successfully connected to service '{name}' via {transport}. Available tools: {tool_count}"
    except Exception as e:
        logger.error(f"Failed to register service {name}: {e}", exc_info=True)
        return f"Error registering service '{name}': {str(e)}"
