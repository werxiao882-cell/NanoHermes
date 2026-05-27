"""Cronjob 工具：管理定时任务。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def cronjob(action: str = "", job_id: str = "", schedule: str = "", prompt: str = "", task_id: str = None) -> str:
    """管理定时任务。"""
    if action == "list":
        return json.dumps({
            "status": "success",
            "jobs": [],
            "message": "No cron jobs configured."
        }, ensure_ascii=False)

    return json.dumps({
        "status": "cronjob_requested",
        "action": action,
        "message": "Cron job management is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="cronjob",
    toolset="cronjob",
    schema={
        "name": "cronjob",
        "description": "管理定时任务。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（list, add, edit, pause, resume, run, remove）。"},
                "job_id": {"type": "string", "description": "任务 ID。"},
                "schedule": {"type": "string", "description": "调度表达式。"},
                "prompt": {"type": "string", "description": "任务提示。"},
            },
            "required": ["action"],
        },
    },
    handler=cronjob,
    description="管理定时任务",
)
