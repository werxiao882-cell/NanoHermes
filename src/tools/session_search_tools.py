"""Session Search 工具：历史会话搜索。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def session_search(query: str = "", session_id: str = "", limit: int = 10, task_id: str = None) -> str:
    """搜索历史会话。"""
    return json.dumps({
        "status": "search_requested",
        "query": query,
        "message": "Session search is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="session_search",
    toolset="session_search",
    schema={
        "name": "session_search",
        "description": "搜索历史会话。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词。"},
                "session_id": {"type": "string", "description": "指定会话 ID。"},
                "limit": {"type": "integer", "description": "最大结果数。"},
            },
            "required": [],
        },
    },
    handler=session_search,
    description="历史会话搜索",
)
