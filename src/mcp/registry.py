"""
MCP 工具注册表

管理哪些 NanoHermes 内部工具暴露为 MCP 工具。
支持白名单/黑名单过滤和工具名称 kebab-case 转换。
"""

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def to_kebab_case(name: str) -> str:
    """将工具名称转换为 kebab-case 格式"""
    s1 = re.sub(r'([A-Z])', r'-\1', name)
    return s1.lower().replace("_", "-").strip("-")


class McpToolRegistry:
    """MCP 工具注册表"""

    def __init__(
        self,
        include: Optional[Set[str]] = None,
        exclude: Optional[Set[str]] = None,
    ):
        self._tools: Dict[str, Callable] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
        self._include = include
        self._exclude = exclude

    def register_tool(
        self,
        name: str,
        tool_fn: Callable,
        schema: Optional[Dict[str, Any]] = None,
    ) -> None:
        """注册单个工具"""
        kebab_name = to_kebab_case(name)

        if self._include and kebab_name not in self._include:
            logger.debug(f"Tool {kebab_name} not in include list, skipping")
            return

        if self._exclude and kebab_name in self._exclude:
            logger.debug(f"Tool {kebab_name} in exclude list, skipping")
            return

        self._tools[kebab_name] = tool_fn
        if schema:
            self._schemas[kebab_name] = schema
        logger.info(f"Registered MCP tool: {kebab_name}")

    def register_tools(self, tools: Dict[str, tuple[Callable, Optional[Dict[str, Any]]]]) -> None:
        """批量注册工具"""
        for name, (tool_fn, schema) in tools.items():
            self.register_tool(name, tool_fn, schema)

    def get_tools(self) -> Dict[str, Callable]:
        """获取所有已注册的工具"""
        return self._tools.copy()

    def get_schemas(self) -> Dict[str, Dict[str, Any]]:
        """获取所有已注册的 schema"""
        return self._schemas.copy()

    def get_tool_names(self) -> List[str]:
        """获取所有已注册的工具名称"""
        return list(self._tools.keys())


def apply_registry_to_server(mcp, registry: McpToolRegistry) -> None:
    """将注册表中的所有工具应用到 FastMCP 实例"""
    tools = registry.get_tools()
    schemas = registry.get_schemas()

    for name, tool_fn in tools.items():
        schema = schemas.get(name, {})

        if schema:
            mcp.tool()(tool_fn)
        else:
            mcp.tool()(tool_fn)

        logger.debug(f"Applied tool {name} to MCP server")
