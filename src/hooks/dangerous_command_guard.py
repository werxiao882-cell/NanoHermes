"""危险命令拦截器。

在模型调用 terminal 工具前，检测命令是否危险，
如果危险则直接阻断，返回拒绝消息。

复用 terminal.py 已有的 DANGEROUS_PATTERNS 检测逻辑，
不重复定义危险命令模式。

使用方式：
    loop.events.intercept(EventType.TOOL_START, dangerous_command_guard, priority=10)
"""

import json
import logging
import re
from typing import Any

from src.conversation.events import ChainResult

logger = logging.getLogger(__name__)

# 复用 terminal.py 已有的危险命令模式
from src.tools.impls.terminal import DANGEROUS_PATTERNS


def dangerous_command_guard(data: dict[str, Any], next_fn) -> None:
    """危险命令拦截器。

    拦截 TOOL_START 事件，对 terminal 工具的命令进行危险模式检测。
    如果匹配危险模式，阻断执行并返回拒绝消息。

    设计理由：
    - 在事件层拦截，不修改 terminal.py 的执行逻辑
    - 复用 DANGEROUS_PATTERNS，避免重复定义
    - 拦截后观察者仍触发，TUI 可显示拦截记录
    - 可通过 priority 控制执行顺序

    Args:
        data: 事件数据，包含 tool_name, tool_args, tool_call。
        next_fn: 责任链下一个拦截器的调用函数。
    """
    tool_name = data.get("tool_name", "")

    # 只拦截 terminal 工具
    if tool_name != "terminal":
        next_fn()
        return

    # 解析命令
    tool_args_raw = data.get("tool_args", "{}")
    try:
        tool_args = json.loads(tool_args_raw) if isinstance(tool_args_raw, str) else tool_args_raw
    except (json.JSONDecodeError, TypeError):
        # 解析失败，放行
        next_fn()
        return

    command = tool_args.get("command", "")
    if not command:
        next_fn()
        return

    # 危险命令检测（复用 terminal.py 的模式）
    for pattern, description in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            logger.warning(f"危险命令被拦截: {description} - {command[:80]}")
            return  # 不调用 next_fn = 阻断

    next_fn()
