"""Delegation 工具：子 Agent 委托。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def delegate_task(goal: str = "", tasks: list[dict] = None, role: str = "leaf",
                  toolsets: list[str] = None, context: str = "", task_id: str = None) -> str:
    """生成子 Agent 执行任务。"""
    return json.dumps({
        "status": "delegation_requested",
        "goal": goal,
        "role": role,
        "message": "Delegation is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="delegate_task",
    toolset="delegation",
    schema={
        "name": "delegate_task",
        "description": "生成子 Agent 执行任务。",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "单任务目标。"},
                "tasks": {"type": "array", "description": "批量任务列表。"},
                "role": {"type": "string", "description": "角色（leaf/orchestrator）。"},
                "toolsets": {"type": "array", "description": "允许的工具集。"},
                "context": {"type": "string", "description": "上下文信息。"},
            },
            "required": [],
        },
    },
    handler=delegate_task,
    description="子 Agent 委托",
)
