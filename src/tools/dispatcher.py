"""工具分发器。

按工具名查找并执行 handler，统一处理：
1. 工具查找
2. 可用性检查
3. 参数映射
4. task_id 传播
5. 错误包装（所有异常转为 JSON 错误字符串）
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.tools.registry import ToolRegistry
from src.tools.availability import check_tool_availability
from src.tools.async_bridge import async_bridge

logger = logging.getLogger(__name__)


def dispatch(
    name: str,
    args: dict[str, Any] | None = None,
    task_id: str | None = None,
) -> str:
    """分发工具调用。

    执行流程：
    1. 按名称查找 ToolEntry
    2. 检查工具可用性（check_fn）
    3. 执行 handler（同步直接调用，异步通过 async_bridge）
    4. 返回结果字符串
    5. 任何异常包装为 JSON 错误字符串

    Args:
        name: 工具名称。
        args: 工具参数字典。
        task_id: 任务 ID，用于日志和会话关联。

    Returns:
        工具执行结果（JSON 字符串）。
    """
    # 步骤 1: 查找工具
    entry = ToolRegistry.get_tool(name)
    if entry is None:
        return json.dumps({
            "error": f"工具未找到: '{name}'。已注册的工具: "
                     f"{', '.join(ToolRegistry.get_all_tools())}"
        })

    # 步骤 2: 检查可用性
    if entry.check_fn and not check_tool_availability(entry.check_fn):
        return json.dumps({
            "error": f"工具不可用: '{name}'。检查函数返回 False。"
        })

    # 步骤 3: 执行 handler
    try:
        call_args = args or {}

        if entry.is_async:
            # 异步工具通过桥接执行
            result = async_bridge(entry.handler, call_args, task_id)
        else:
            # 同步工具直接调用
            result = entry.handler(**call_args, task_id=task_id)

        return result

    except Exception as e:
        # 步骤 4: 错误包装
        logger.error(f"工具执行失败 '{name}': {e}", exc_info=True)
        return json.dumps({
            "error": f"工具执行失败: {type(e).__name__}: {e}"
        })
