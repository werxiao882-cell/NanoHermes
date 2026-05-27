"""clarify - 向用户提问，支持预设选项和自定义输入。

当 Agent 需要用户澄清或决策时，弹出选择框，支持：
- 预设选项（最多 4 个）
- 用户自定义输入
"""

from __future__ import annotations

import json
from typing import Any

# 全局存储澄清请求，等待用户响应
_pending_clarification: dict[str, Any] | None = None


def clarify(
    question: str = "",
    options: list[str] | None = None,
    allow_custom: bool = True,
    task_id: str = None,
) -> str:
    """向用户提问，支持预设选项和自定义输入。

    Args:
        question: 要问的问题。
        options: 预设选项列表（最多 4 个）。
        allow_custom: 是否允许用户自定义输入。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含澄清请求状态。
    """
    global _pending_clarification

    # 限制选项数量
    if options:
        options = options[:4]

    _pending_clarification = {
        "question": question,
        "options": options or [],
        "allow_custom": allow_custom,
        "status": "pending",
    }

    return json.dumps({
        "status": "clarification_requested",
        "question": question,
        "options": options or [],
        "allow_custom": allow_custom,
        "message": "Waiting for user response..."
    }, ensure_ascii=False)


def get_pending_clarification() -> dict[str, Any] | None:
    """获取待处理的澄清请求。

    Returns:
        澄清请求字典，如果没有待处理的则返回 None。
    """
    return _pending_clarification


def respond_to_clarification(response: str) -> str:
    """响应用户的澄清回答。

    Args:
        response: 用户的回答。

    Returns:
        JSON 字符串，包含响应状态。
    """
    global _pending_clarification

    if _pending_clarification is None:
        return json.dumps({
            "error": "No pending clarification request."
        }, ensure_ascii=False)

    _pending_clarification["status"] = "answered"
    _pending_clarification["response"] = response

    return json.dumps({
        "status": "success",
        "response": response,
        "message": "User response recorded."
    }, ensure_ascii=False)


def clear_pending_clarification() -> None:
    """清除待处理的澄清请求。"""
    global _pending_clarification
    _pending_clarification = None
