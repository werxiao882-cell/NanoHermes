"""技能审查后台任务。

提供技能审查任务的处理器和触发条件，供 BackgroundTaskScheduler 注册使用。

设计决策：
- 通过 run_background_review() 执行审查，不直接依赖 background_review 内部实现
- 触发条件：对话轮数 >= 10 且距离上次审查 >= 30 分钟
- 审查最近 20 条消息（10 轮对话），每条截断到 500 字符
- 通过 fork_agent 调用 skill_manage 工具创建或更新技能
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# 触发阈值
SKILL_REVIEW_MIN_TURNS = 10  # 至少 10 轮对话
SKILL_REVIEW_MIN_INTERVAL_SECONDS = 1800  # 至少 30 分钟间隔

# 上次审查时间戳
_last_review_time: float = 0.0

# 最多审查的消息数
SKILL_REVIEW_MAX_MESSAGES = 20


def skill_review_handler(event_data: dict[str, Any]) -> dict[str, Any]:
    """技能审查任务处理器。

    通过 run_background_review() 执行技能审查。

    Args:
        event_data: 事件数据字典，包含：
            - messages: 对话消息列表
            - model_caller: 模型调用函数
            - tool_dispatch: 工具分发函数
            - tool_schemas: 工具 schema 列表（可选）

    Returns:
        审查结果字典。
    """
    global _last_review_time

    messages = event_data.get("messages", [])
    model_caller = event_data.get("model_caller")
    tool_dispatch = event_data.get("tool_dispatch")
    tool_schemas = event_data.get("tool_schemas")

    if not model_caller:
        logger.warning("技能审查：未提供 model_caller")
        return {"reviewed": False, "error": "no_model_caller"}

    if not tool_dispatch:
        logger.warning("技能审查：未提供 tool_dispatch")
        return {"reviewed": False, "error": "no_tool_dispatch"}

    # 截取最近的消息
    recent_messages = messages[-SKILL_REVIEW_MAX_MESSAGES:] if len(messages) > SKILL_REVIEW_MAX_MESSAGES else messages

    from src.background.review import run_background_review

    result = run_background_review(
        messages=recent_messages,
        model_call=model_caller,
        tool_dispatch=tool_dispatch,
        review_type="skill",
        tool_schemas=tool_schemas,
    )

    # 更新上次审查时间
    _last_review_time = time.time()

    return {
        "reviewed": not result.get("error"),
        "iterations": result.get("iterations", 0),
        "response": result.get("final_response", ""),
        "elapsed": result.get("elapsed", 0),
    }


def skill_review_trigger(event_data: dict[str, Any]) -> bool:
    """技能审查触发条件。

    检查对话轮数是否达到阈值，且距离上次审查超过间隔。

    Args:
        event_data: 事件数据字典，包含 messages 和 iteration 字段。

    Returns:
        是否应该触发技能审查。
    """
    iteration = event_data.get("iteration", 0)

    # 检查对话轮数
    if iteration < SKILL_REVIEW_MIN_TURNS:
        logger.debug(f"技能审查：迭代数 {iteration} < {SKILL_REVIEW_MIN_TURNS}，跳过")
        return False

    # 检查时间间隔
    now = time.time()
    elapsed = now - _last_review_time
    if elapsed < SKILL_REVIEW_MIN_INTERVAL_SECONDS:
        logger.debug(f"技能审查：距离上次审查 {elapsed:.0f}s < {SKILL_REVIEW_MIN_INTERVAL_SECONDS}s，跳过")
        return False

    logger.debug(f"技能审查：迭代数 {iteration} >= {SKILL_REVIEW_MIN_TURNS}，触发")
    return True


def register_skill_review_task(
    scheduler,
    model_caller,
    tool_dispatch,
    tool_schemas=None,
    enabled: bool = True,
) -> None:
    """注册技能审查任务到调度器。

    创建一个闭包处理器，将必要的依赖注入到 event_data 中。

    Args:
        scheduler: BackgroundTaskScheduler 实例。
        model_caller: 模型调用函数。
        tool_dispatch: 工具分发函数。
        tool_schemas: 工具 schema 列表（可选）。
        enabled: 是否启用任务。
    """
    def handler_with_deps(event_data: dict[str, Any]) -> dict[str, Any]:
        """带依赖注入的处理器。"""
        event_data["model_caller"] = model_caller
        event_data["tool_dispatch"] = tool_dispatch
        if tool_schemas:
            event_data["tool_schemas"] = tool_schemas

        return skill_review_handler(event_data)

    scheduler.register_task(
        name="skill_review",
        handler=handler_with_deps,
        trigger=skill_review_trigger,
        enabled=enabled,
    )

    logger.info(f"技能审查任务已注册 (enabled={enabled})")


def reset_last_review_time() -> None:
    """重置上次审查时间（用于测试）。"""
    global _last_review_time
    _last_review_time = 0.0
