"""Code Execution 工具：运行 Python 脚本。"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


def execute_code(code: str = "", language: str = "python", task_id: str = None) -> str:
    """运行 Python 脚本，可以调用 Hermes 工具。"""
    return json.dumps({
        "status": "code_execution_requested",
        "language": language,
        "code_length": len(code),
        "message": "Code execution is not available in this version."
    }, ensure_ascii=False)


register_tool(
    name="execute_code",
    toolset="code_execution",
    schema={
        "name": "execute_code",
        "description": "运行 Python 脚本，可以调用 Hermes 工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "要执行的 Python 代码。"},
                "language": {"type": "string", "description": "编程语言（默认 python）。"},
            },
            "required": ["code"],
        },
    },
    handler=execute_code,
    description="运行 Python 脚本",
)
