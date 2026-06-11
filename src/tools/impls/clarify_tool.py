"""Clarify 工具：向用户提问，支持预设选项和自定义输入。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.core.registry import register_tool

# 全局存储澄清请求，等待用户响应
_pending_clarification: dict[str, Any] | None = None


def clarify(question: str = "", choices: list = None, allow_custom: bool = True, task_id: str = None, **kwargs) -> str:
    """向用户提问，支持预设选项和自定义输入。

    Args:
        question: 要问的问题。
        choices: 预设选项列表（最多 4 个）。
        allow_custom: 是否允许用户自定义输入。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含提问状态。
    """
    global _pending_clarification

    if choices:
        choices = choices[:4]

    _pending_clarification = {
        "question": question,
        "choices": choices or [],
        "allow_custom": allow_custom,
        "status": "pending",
    }

    return json.dumps({
        "status": "clarification_requested",
        "question": question,
        "choices": choices or [],
        "allow_custom": allow_custom,
        "message": "Waiting for user response..."
    }, ensure_ascii=False)


def get_pending_clarification() -> dict[str, Any] | None:
    """获取待处理的澄清请求。"""
    return _pending_clarification


def respond_to_clarification(response: str) -> str:
    """响应用户的澄清回答。"""
    global _pending_clarification

    if _pending_clarification is None:
        return json.dumps({"error": "No pending clarification request."}, ensure_ascii=False)

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


# 注册工具
register_tool(
    name="clarify",
    toolset="clarify",
    schema={
        "name": "clarify",
        "description": (
            "Ask the user a question when you need clarification, feedback, or a decision before proceeding. "
            "Supports two modes:\n\n"
            "1. **Multiple choice** — provide up to 4 choices. The user picks one or types their own answer via a 5th 'Other' option.\n"
            "2. **Open-ended** — omit choices entirely. The user types a free-form response.\n\n"
            "Use this tool when:\n"
            "- The task is ambiguous and you need the user to choose an approach\n"
            "- You want post-task feedback ('How did that work out?')\n"
            "- You want to offer to save a skill or update memory\n"
            "- A decision has meaningful trade-offs the user should weigh in on\n\n"
            "Do NOT use this tool for simple yes/no confirmation of dangerous commands (the terminal tool handles that). "
            "Prefer making a reasonable default choice yourself when the decision is low-stakes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The question to present to the user."
                },
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": 4,
                    "description": "Up to 4 answer choices. Omit this parameter entirely to ask an open-ended question. When provided, the UI automatically appends an 'Other (type your answer)' option."
                }
            },
            "required": ["question"],
        },
    },
    handler=clarify,
    description="向用户提问",
    defer_loading=True,
)
