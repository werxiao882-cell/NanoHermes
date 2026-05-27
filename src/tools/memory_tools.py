"""Memory 工具：持久记忆。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def memory(action: str = "", content: str = "", key: str = "", task_id: str = None) -> str:
    """保存持久记忆，跨会话保留。"""
    return json.dumps({
        "status": "memory_requested",
        "action": action,
        "message": "Memory management is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="memory",
    toolset="memory",
    schema={
        "name": "memory",
        "description": "保存持久记忆，跨会话保留。",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "操作类型（add, replace, remove, view）。"},
                "content": {"type": "string", "description": "记忆内容。"},
                "key": {"type": "string", "description": "记忆键。"},
            },
            "required": ["action"],
        },
    },
    handler=memory,
    description="持久记忆",
)
