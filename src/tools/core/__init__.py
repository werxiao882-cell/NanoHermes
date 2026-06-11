"""工具核心模块。

提供工具系统的核心基础设施：注册表、分发器、可用性检查和搜索引擎。
"""

from src.tools.core.registry import (
    ToolEntry,
    ToolRegistry,
    register_tool,
    get_tool,
    get_all_tools,
    get_tool_schemas,
    get_deferred_tools,
    discover_tools,
)
from src.tools.core.dispatcher import dispatch, dispatch_batch
from src.tools.core.availability import check_tool_availability

__all__ = [
    "ToolEntry",
    "ToolRegistry",
    "register_tool",
    "get_tool",
    "get_all_tools",
    "get_tool_schemas",
    "get_deferred_tools",
    "discover_tools",
    "dispatch",
    "dispatch_batch",
    "check_tool_availability",
]
