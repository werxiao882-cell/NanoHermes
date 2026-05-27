"""Process 工具：后台进程管理。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def process(action: str = "", process_id: str = "", task_id: str = None) -> str:
    """管理后台进程。"""
    return json.dumps({
        "status": "process_requested",
        "action": action,
        "message": "Process management is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="process",
    toolset="terminal",
    schema={
        "name": "process",
        "description": "管理后台进程。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（list, stop, kill, output）。"},
                "process_id": {"type": "string", "description": "进程 ID。"},
            },
            "required": ["action"],
        },
    },
    handler=process,
    description="后台进程管理",
)
