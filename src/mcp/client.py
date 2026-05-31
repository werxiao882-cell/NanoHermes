"""
MCP 客户端连接管理

支持通过 3 种传输协议连接外部 MCP 服务：
- Stdio（子进程启动）
- Streamable HTTP（HTTP POST + SSE）
- HTTP+SSE（旧版兼容）
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path.home() / ".nanohermes" / "mcp_servers.json"
CONNECTION_TIMEOUT = 30


@dataclass
class McpServiceConfig:
    """MCP 服务配置"""
    name: str
    transport: str
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    is_active: bool = True


class McpClientManager:
    """MCP 客户端连接管理器"""

    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._contexts: Dict[str, Any] = {}
        self._services: Dict[str, McpServiceConfig] = {}

    async def connect_stdio(self, name: str, command: str, args: List[str], env: Optional[Dict[str, str]] = None) -> ClientSession:
        """通过 Stdio 连接外部 MCP 服务"""
        if name in self._sessions:
            logger.info(f"Reusing existing session for {name}")
            return self._sessions[name]

        server_params = StdioServerParameters(
            command=command,
            args=args,
            env=env or {},
        )

        ctx = stdio_client(server_params)
        read_write = await ctx.__aenter__()
        session = ClientSession(read_write[0], read_write[1])
        await session.__aenter__()
        await session.initialize()

        self._sessions[name] = session
        self._contexts[name] = ctx
        logger.info(f"Connected to {name} via stdio")
        return session

    async def connect_streamable_http(self, name: str, url: str) -> ClientSession:
        """通过 Streamable HTTP 连接外部 MCP 服务"""
        if name in self._sessions:
            logger.info(f"Reusing existing session for {name}")
            return self._sessions[name]

        try:
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError:
            raise ImportError("mcp[cli] is required for Streamable HTTP support")

        ctx = streamablehttp_client(url)
        read_write = await ctx.__aenter__()
        session = ClientSession(read_write[0], read_write[1])
        await session.__aenter__()
        await session.initialize()

        self._sessions[name] = session
        self._contexts[name] = ctx
        logger.info(f"Connected to {name} via streamable-http at {url}")
        return session

    async def connect_sse(self, name: str, url: str) -> ClientSession:
        """通过 HTTP+SSE 连接外部 MCP 服务（旧版兼容）"""
        if name in self._sessions:
            logger.info(f"Reusing existing session for {name}")
            return self._sessions[name]

        try:
            from mcp.client.sse import sse_client
        except ImportError:
            raise ImportError("mcp[cli] is required for SSE support")

        ctx = sse_client(url)
        read_write = await ctx.__aenter__()
        session = ClientSession(read_write[0], read_write[1])
        await session.__aenter__()
        await session.initialize()

        self._sessions[name] = session
        self._contexts[name] = ctx
        logger.info(f"Connected to {name} via SSE at {url}")
        return session

    async def connect_service(self, config: McpServiceConfig) -> ClientSession:
        """根据配置连接 MCP 服务"""
        if config.transport == "stdio":
            return await self.connect_stdio(
                config.name,
                config.command,
                config.args or [],
                config.env,
            )
        elif config.transport == "streamable-http":
            return await self.connect_streamable_http(config.name, config.url)
        elif config.transport == "sse":
            return await self.connect_sse(config.name, config.url)
        else:
            raise ValueError(f"Unknown transport type: {config.transport}")

    async def call_tool(self, service: str, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """调用外部 MCP 服务的工具"""
        if service not in self._sessions:
            raise ConnectionError(f"Service {service} is not connected. Call connect_service() first.")

        session = self._sessions[service]
        result = await session.call_tool(tool_name, arguments or {})
        return result

    async def list_tools(self, service: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """列出已连接服务的工具"""
        if service:
            if service not in self._sessions:
                raise ConnectionError(f"Service {service} is not connected")
            session = self._sessions[service]
            tools_result = await session.list_tools()
            return {service: [t.model_dump() for t in tools_result.tools]}

        all_tools = {}
        for svc_name, session in self._sessions.items():
            tools_result = await session.list_tools()
            all_tools[svc_name] = [t.model_dump() for t in tools_result.tools]
        return all_tools

    async def disconnect(self, service: str) -> None:
        """断开与指定服务的连接"""
        if service in self._sessions:
            await self._sessions[service].__aexit__(None, None, None)
            await self._contexts[service].__aexit__(None, None, None)
            del self._sessions[service]
            del self._contexts[service]
            logger.info(f"Disconnected from {service}")

    async def disconnect_all(self) -> None:
        """断开所有连接"""
        for service in list(self._sessions.keys()):
            await self.disconnect(service)


def load_service_config(config_path: Optional[Path] = None) -> List[McpServiceConfig]:
    """从 JSON 配置文件加载服务配置"""
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        logger.warning(f"MCP config file not found at {path}")
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse MCP config file: {e}")
        return []

    services = []
    mcp_servers = data.get("mcpServers", {})

    for name, config in mcp_servers.items():
        is_active = config.get("isActive", True)
        if not is_active:
            logger.debug(f"Skipping inactive service: {name}")
            continue

        service = McpServiceConfig(
            name=name,
            transport=config.get("type", "stdio"),
            command=config.get("command"),
            args=config.get("args"),
            env=config.get("env"),
            url=config.get("url"),
            is_active=is_active,
        )
        services.append(service)

    return services
