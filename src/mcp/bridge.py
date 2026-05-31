"""
工具桥接层

将 NanoHermes 内部工具函数转换为 MCP 兼容格式。
支持参数 Schema 转换（Pydantic → JSON Schema）和返回值格式化。
"""

import inspect
import logging
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


def pydantic_to_json_schema(model: type[BaseModel]) -> Dict[str, Any]:
    """将 Pydantic model 转换为 JSON Schema"""
    return model.model_json_schema()


def format_success_response(result: Any) -> Dict[str, Any]:
    """格式化成功响应为 MCP 标准格式"""
    return {
        "content": [
            {
                "type": "text",
                "text": str(result) if not isinstance(result, str) else result,
            }
        ],
        "isError": False,
    }


def format_error_response(error: Exception) -> Dict[str, Any]:
    """格式化错误响应为 MCP 标准格式"""
    return {
        "content": [
            {
                "type": "text",
                "text": f"Error: {str(error)}",
            }
        ],
        "isError": True,
    }


def bridge_tool(tool_fn: Callable) -> Callable:
    """
    桥接 NanoHermes 工具函数为 MCP 兼容格式

    - 转换参数 schema（Pydantic → JSON Schema）
    - 统一错误处理和返回值格式
    """
    sig = inspect.signature(tool_fn)
    tool_name = tool_fn.__name__.replace("_", "-")

    async def wrapped(**kwargs) -> Dict[str, Any]:
        try:
            result = tool_fn(**kwargs)
            if inspect.iscoroutine(result):
                result = await result
            return format_success_response(result)
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}", exc_info=True)
            return format_error_response(e)

    wrapped.__name__ = tool_fn.__name__
    wrapped.__doc__ = tool_fn.__doc__
    wrapped._original_fn = tool_fn

    return wrapped


def bridge_tool_with_schema(tool_fn: Callable, param_model: Optional[type[BaseModel]] = None) -> tuple[str, Callable, Dict[str, Any]]:
    """
    桥接工具并返回 (名称, 函数, JSON Schema)

    返回元组用于 MCP 工具注册。
    """
    wrapped = bridge_tool(tool_fn)
    tool_name = tool_fn.__name__.replace("_", "-")

    schema = {}
    if param_model:
        schema = pydantic_to_json_schema(param_model)
    else:
        sig = inspect.signature(tool_fn)
        properties = {}
        required = []
        for name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"

            properties[name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(name)

        schema = {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    return tool_name, wrapped, schema
