"""Clarify 工具：向用户提问，支持预设选项和自定义输入。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool

# 全局存储澄清请求，等待用户响应
_pending_clarification: dict[str, Any] | None = None


def clarify(question: str = "", options: list = None, allow_custom: bool = True, task_id: str = None) -> str:
    """向用户提问，支持预设选项和自定义输入。

    Args:
        question: 要问的问题。
        options: 预设选项列表（最多 4 个）。
        allow_custom: 是否允许用户自定义输入。
        task_id: 任务 ID。

    Returns:
        JSON 字符串，包含提问状态。
    """
    global _pending_clarification

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
        "description": "向用户提问，支持预设选项和自定义输入。",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "要问的问题。"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "预设选项列表（最多 4 个）。",
                },
                "allow_custom": {
                    "type": "boolean",
                    "description": "是否允许用户自定义输入（默认 true）。",
                },
            },
            "required": ["question"],
        },
    },
    handler=clarify,
    description="向用户提问",
)
