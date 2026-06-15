"""Memory 工具：持久记忆。

委托 MemoryStore 执行所有记忆操作，不再直接操作文件。
通过全局单例访问 MemoryStore（工具注册时无法注入实例），
FileMemoryProvider 通过构造函数注入同一个 MemoryStore 实例。

设计理由：
memory_tool.py 通过全局单例访问 MemoryStore（工具注册时无法注入实例），
FileMemoryProvider 通过构造函数注入 MemoryStore（由 TUIApp 创建并传递），
两者指向同一个 MemoryStore 实例（通过模块级缓存保证）。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from src.tools.core.registry import register_tool

logger = logging.getLogger(__name__)

_store: Optional[Any] = None


def get_memory_store() -> Any:
    """获取全局 MemoryStore 单例。

    延迟初始化：首次调用时创建 MemoryStore 并从磁盘加载。
    如果已通过 set_memory_store() 注入，则返回注入的实例。
    """
    global _store
    if _store is None:
        from src.memory.memory_store import MemoryStore
        memory_dir = Path.home() / ".nanohermes" / "memory"
        _store = MemoryStore(memory_dir)
        _store.load_from_disk()
    return _store


def set_memory_store(store: Any) -> None:
    """注入 MemoryStore 实例（由 TUIApp 或 FileMemoryProvider 调用）。

    确保 memory_tool.py 和 FileMemoryProvider 共享同一个 MemoryStore 实例。
    """
    global _store
    _store = store


def memory(
    action: str = "",
    target: str = "memory",
    content: str = "",
    old_text: str = "",
    key: str = "",
    task_id: str = None,
    **kwargs,
) -> str:
    """持久记忆工具。

    保存跨会话的持久信息。委托 MemoryStore 执行所有操作。

    何时保存（主动执行，不要等待被要求）：
    - 用户纠正你或说"记住这个"/"别再那样做"
    - 用户分享偏好、习惯或个人信息
    - 发现环境信息（OS、已安装工具、项目结构）
    - 学习到特定用户的约定、API 怪癖或工作流

    优先级：用户偏好和纠正 > 环境事实 > 程序性知识
    """
    if target not in ("memory", "user"):
        return json.dumps({
            "success": False,
            "error": f"Invalid target '{target}'. Use 'memory' or 'user'."
        }, ensure_ascii=False)

    try:
        store = get_memory_store()

        if action == "add":
            result = store.add(target, content)

        elif action == "replace":
            result = store.replace(target, old_text, content)

        elif action == "remove":
            result = store.remove(target, old_text)

        elif action == "view":
            entries_m = store.memory_entries
            entries_u = store.user_entries
            result = {
                "success": True,
                "action": "view",
                "memory": entries_m,
                "user": entries_u,
                "message": "Current memory contents.",
            }

        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown action '{action}'. Use: add, replace, remove, view"
            }, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Memory tool error: {e}", exc_info=True)
        return json.dumps({
            "success": False,
            "error": f"Memory operation failed: {str(e)}"
        }, ensure_ascii=False)


def check_memory_requirements() -> bool:
    return True


register_tool(
    name="memory",
    toolset="memory",
    schema={
        "name": "memory",
        "description": (
            "Save durable information to persistent memory that survives across sessions. Memory is injected into future turns, so keep it compact and focused on facts that will still matter later.\n\n"
            "WHEN TO SAVE (do this proactively, don't wait to be asked):\n"
            "- User corrects you or says 'remember this' / 'don't do that again'\n"
            "- User shares a preference, habit, or personal detail (name, role, timezone, coding style)\n"
            "- You discover something about the environment (OS, installed tools, project structure)\n"
            "- You learn a convention, API quirk, or workflow specific to this user's setup\n"
            "- You identify a stable fact that will be useful again in future sessions\n\n"
            "PRIORITY: User preferences and corrections > environment facts > procedural knowledge. The most valuable memory prevents the user from having to repeat themselves.\n\n"
            "Do NOT save task progress, session outcomes, completed-work logs, or temporary TODO state to memory; use session_search to recall those from past transcripts.\n"
            "If you've discovered a new way to do something, solved a problem that could be necessary later, save it as a skill with the skill tool.\n\n"
            "TWO TARGETS:\n"
            "- 'user': who the user is -- name, role, preferences, communication style, pet peeves\n"
            "- 'memory': your notes -- environment facts, project conventions, tool quirks, lessons learned\n\n"
            "ACTIONS: add (new entry), replace (update existing -- old_text identifies it), remove (delete -- old_text identifies it).\n\n"
            "SKIP: trivial/obvious info, things easily re-discovered, raw data dumps, and temporary task state."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "replace", "remove"],
                    "description": "The action to perform."
                },
                "target": {
                    "type": "string",
                    "enum": ["memory", "user"],
                    "description": "Which memory store: 'memory' for personal notes, 'user' for user profile."
                },
                "content": {
                    "type": "string",
                    "description": "The entry content. Required for 'add' and 'replace'."
                },
                "old_text": {
                    "type": "string",
                    "description": "Short unique substring identifying the entry to replace or remove."
                },
            },
            "required": ["action", "target"],
        },
    },
    handler=memory,
    check_fn=check_memory_requirements,
    description="持久记忆",
    defer_loading=True,
)
