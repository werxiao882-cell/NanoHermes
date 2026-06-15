"""记忆刷写后台任务。

提供记忆刷写任务的处理器和触发条件，供 BackgroundTaskScheduler 注册使用。

设计决策：
- 通过 run_background_review() 执行审查，不直接依赖 background_review 内部实现
- 触发条件：消息数 >= 10（5 轮对话）
- 提取最近 20 条消息（10 轮对话），每条截断到 500 字符
- 通过 tool_dispatch_override 将 memory 工具路由到 FileMemoryProvider
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 触发阈值：至少 10 条消息（5 轮对话）才触发记忆刷写
MEMORY_FLUSH_MIN_MESSAGES = 10

# 最多审查的消息数
MEMORY_FLUSH_MAX_MESSAGES = 20


def memory_flush_handler(event_data: dict[str, Any]) -> dict[str, Any]:
    """记忆刷写任务处理器。

    通过 run_background_review() 执行记忆审查。
    创建自定义 tool_dispatch_override 将 memory 工具路由到 FileMemoryProvider。

    Args:
        event_data: 事件数据字典，包含：
            - messages: 对话消息列表
            - memory_provider: FileMemoryProvider 实例
            - model_caller: 模型调用函数
            - tool_dispatch: 工具分发函数
            - tool_schemas: 工具 schema 列表（可选）

    Returns:
        提取结果字典。
    """
    messages = event_data.get("messages", [])
    memory_provider = event_data.get("memory_provider")
    model_caller = event_data.get("model_caller")
    tool_schemas = event_data.get("tool_schemas")

    if not memory_provider:
        logger.warning("记忆刷写：未提供 memory_provider")
        return {"extracted": 0, "error": "no_memory_provider"}

    if not model_caller:
        logger.warning("记忆刷写：未提供 model_caller")
        return {"extracted": 0, "error": "no_model_caller"}

    # 创建自定义工具分发器：将 memory 工具路由到 FileMemoryProvider
    def memory_dispatch(tool_name: str, args: dict) -> str:
        if tool_name == "memory":
            return memory_provider.handle_tool_call(tool_name, args)
        return json.dumps({"error": f"Tool '{tool_name}' not allowed in memory review"})

    # 截取最近的消息
    recent_messages = messages[-MEMORY_FLUSH_MAX_MESSAGES:] if len(messages) > MEMORY_FLUSH_MAX_MESSAGES else messages

    from src.background.review import run_background_review

    result = run_background_review(
        messages=recent_messages,
        model_call=model_caller,
        tool_dispatch=memory_dispatch,
        review_type="memory",
        tool_schemas=tool_schemas,
        tool_dispatch_override=memory_dispatch,
    )

    return {
        "extracted": result.get("iterations", 0),
        "response": result.get("final_response", ""),
        "elapsed": result.get("elapsed", 0),
        "error": result.get("error", ""),
    }


def memory_flush_trigger(event_data: dict[str, Any]) -> bool:
    """记忆刷写触发条件。

    检查消息数是否达到阈值。

    Args:
        event_data: 事件数据字典，包含 messages 字段。

    Returns:
        是否应该触发记忆刷写。
    """
    messages = event_data.get("messages", [])
    message_count = len(messages)

    if message_count < MEMORY_FLUSH_MIN_MESSAGES:
        logger.debug(f"记忆刷写：消息数 {message_count} < {MEMORY_FLUSH_MIN_MESSAGES}，跳过")
        return False

    logger.debug(f"记忆刷写：消息数 {message_count} >= {MEMORY_FLUSH_MIN_MESSAGES}，触发")
    return True


def register_memory_flush_task(
    scheduler,
    memory_provider,
    model_caller,
    tool_dispatch,
    tool_schemas=None,
    enabled: bool = True,
) -> None:
    """注册记忆刷写任务到调度器。

    创建一个闭包处理器，将必要的依赖注入到 event_data 中。

    Args:
        scheduler: BackgroundTaskScheduler 实例。
        memory_provider: FileMemoryProvider 实例。
        model_caller: 模型调用函数。
        tool_dispatch: 工具分发函数。
        tool_schemas: 工具 schema 列表（可选）。
        enabled: 是否启用任务。
    """
    def handler_with_deps(event_data: dict[str, Any]) -> dict[str, Any]:
        """带依赖注入的处理器。"""
        event_data["memory_provider"] = memory_provider
        event_data["model_caller"] = model_caller
        event_data["tool_dispatch"] = tool_dispatch
        if tool_schemas:
            event_data["tool_schemas"] = tool_schemas

        return memory_flush_handler(event_data)

    scheduler.register_task(
        name="memory_flush",
        handler=handler_with_deps,
        trigger=memory_flush_trigger,
        enabled=enabled,
    )

    logger.info(f"记忆刷写任务已注册 (enabled={enabled})")
