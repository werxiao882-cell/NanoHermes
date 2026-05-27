"""Todo 工具：任务计划和管理。

参考 Hermes Agent 的 todo_tool.py 实现，支持：
- 大模型自己制定计划
- 跟踪任务进度
- 任务状态管理（pending/in_progress/completed/cancelled）
- 任务合并和替换逻辑

设计：
- 单个 todo 工具：提供 todos 参数写入，省略则读取
- 每次调用返回完整当前列表
- 不修改系统提示，不修改工具响应
- 行为指导完全在工具 schema 描述中
"""

from __future__ import annotations

import json
from typing import Any

from src.tools.registry import register_tool


# 有效的任务状态值
VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}


class TodoStore:
    """内存任务列表。每个会话一个实例。

    任务按顺序排列 -- 列表位置即优先级。每个任务包含：
      - id: 唯一字符串标识符（由 agent 选择）
      - content: 任务描述
      - status: pending | in_progress | completed | cancelled
    """

    def __init__(self):
        """初始化空任务列表。"""
        self._items: list[dict[str, str]] = []

    def write(self, todos: list[dict[str, Any]], merge: bool = False) -> list[dict[str, str]]:
        """写入任务。返回写入后的完整当前列表。

        Args:
            todos: {id, content, status} 字典列表。
            merge: 如果为 False，替换整个列表。如果为 True，按 id 更新现有任务并追加新任务。

        Returns:
            当前任务列表。
        """
        if not merge:
            # 替换模式：新列表完全替换
            self._items = [self._validate(t) for t in self._dedupe_by_id(todos)]
        else:
            # 合并模式：按 id 更新现有任务，追加新任务
            existing = {item["id"]: item for item in self._items}
            for t in self._dedupe_by_id(todos):
                item_id = str(t.get("id", "")).strip()
                if not item_id:
                    continue  # 没有 id 无法合并

                if item_id in existing:
                    # 更新 LLM 实际提供的字段
                    if "content" in t and t["content"]:
                        existing[item_id]["content"] = str(t["content"]).strip()
                    if "status" in t and t["status"]:
                        status = str(t["status"]).strip().lower()
                        if status in VALID_STATUSES:
                            existing[item_id]["status"] = status
                else:
                    # 新任务 -- 完全验证并追加到末尾
                    validated = self._validate(t)
                    existing[validated["id"]] = validated
                    self._items.append(validated)
            # 重建 _items，保留现有任务的顺序
            seen = set()
            rebuilt = []
            for item in self._items:
                current = existing.get(item["id"], item)
                if current["id"] not in seen:
                    rebuilt.append(current)
                    seen.add(current["id"])
            self._items = rebuilt
        return self.read()

    def read(self) -> list[dict[str, str]]:
        """返回当前列表的副本。"""
        return [item.copy() for item in self._items]

    def has_items(self) -> bool:
        """检查列表中是否有任何任务。"""
        return bool(self._items)

    def format_for_display(self) -> str:
        """格式化任务列表用于显示。

        Returns:
            人类可读的任务列表字符串。
        """
        if not self._items:
            return "No tasks in the list."

        # 状态标记
        markers = {
            "completed": "[x]",
            "in_progress": "[>]",
            "pending": "[ ]",
            "cancelled": "[~]",
        }

        lines = []
        for item in self._items:
            marker = markers.get(item["status"], "[?]")
            lines.append(f"- {marker} {item['id']}. {item['content']} ({item['status']})")

        return "\n".join(lines)

    @staticmethod
    def _validate(item: dict[str, Any]) -> dict[str, str]:
        """验证并规范化任务项。

        确保必需字段存在且状态有效。
        返回只包含 {id, content, status} 的干净字典。

        Args:
            item: 原始任务项字典。

        Returns:
            验证后的任务项字典。
        """
        item_id = str(item.get("id", "")).strip()
        if not item_id:
            item_id = "?"

        content = str(item.get("content", "")).strip()
        if not content:
            content = "(no description)"

        status = str(item.get("status", "pending")).strip().lower()
        if status not in VALID_STATUSES:
            status = "pending"

        return {"id": item_id, "content": content, "status": status}

    @staticmethod
    def _dedupe_by_id(todos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """按 id 去重，保留最后出现的位置。

        Args:
            todos: 原始任务列表。

        Returns:
            去重后的任务列表。
        """
        last_index: dict[str, int] = {}
        for i, item in enumerate(todos):
            item_id = str(item.get("id", "")).strip() or "?"
            last_index[item_id] = i
        return [todos[i] for i in sorted(last_index.values())]


# 全局 TodoStore 实例（每个会话一个）
_todo_store = TodoStore()


def todo_tool(
    todos: list[dict[str, Any]] | None = None,
    merge: bool = False,
) -> str:
    """todo 工具的单一入口点。根据参数读取或写入。

    Args:
        todos: 如果提供，写入这些任务。如果为 None，读取当前列表。
        merge: 如果为 True，按 id 更新。如果为 False（默认），替换整个列表。

    Returns:
        包含完整当前列表和摘要元数据的 JSON 字符串。
    """
    global _todo_store

    if todos is not None:
        items = _todo_store.write(todos, merge)
    else:
        items = _todo_store.read()

    # 构建摘要计数
    pending = sum(1 for i in items if i["status"] == "pending")
    in_progress = sum(1 for i in items if i["status"] == "in_progress")
    completed = sum(1 for i in items if i["status"] == "completed")
    cancelled = sum(1 for i in items if i["status"] == "cancelled")

    return json.dumps({
        "todos": items,
        "summary": {
            "total": len(items),
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "cancelled": cancelled,
        },
    }, ensure_ascii=False)


def get_todo_store() -> TodoStore:
    """获取全局 TodoStore 实例。

    Returns:
        TodoStore 实例。
    """
    return _todo_store


def reset_todo_store() -> None:
    """重置全局 TodoStore 实例（用于测试）。"""
    global _todo_store
    _todo_store = TodoStore()


# ============================================================================
# OpenAI 函数调用 Schema
# ============================================================================
# 行为指导嵌入在描述中，作为静态工具 schema 的一部分（缓存，对话中永不改变）

TODO_SCHEMA = {
    "name": "todo",
    "description": (
        "Manage your task list for the current session. Use for complex tasks "
        "with 3+ steps or when the user provides multiple tasks. "
        "Call with no parameters to read the current list.\n\n"
        "Writing:\n"
        "- Provide 'todos' array to create/update items\n"
        "- merge=false (default): replace the entire list with a fresh plan\n"
        "- merge=true: update existing items by id, add any new ones\n\n"
        "Each item: {id: string, content: string, "
        "status: pending|in_progress|completed|cancelled}\n"
        "List order is priority. Only ONE item in_progress at a time.\n"
        "Mark items completed immediately when done. If something fails, "
        "cancel it and add a revised item.\n\n"
        "Always returns the full current list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "description": "Task items to write. Omit to read current list.",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique item identifier"
                        },
                        "content": {
                            "type": "string",
                            "description": "Task description"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"],
                            "description": "Current status"
                        }
                    },
                    "required": ["id", "content", "status"]
                }
            },
            "merge": {
                "type": "boolean",
                "description": (
                    "true: update existing items by id, add new ones. "
                    "false (default): replace the entire list."
                ),
                "default": False
            }
        },
        "required": []
    }
}


# 注册工具
register_tool(
    name="todo",
    toolset="todo",
    schema=TODO_SCHEMA,
    handler=lambda todos=None, merge=False, task_id=None: todo_tool(todos=todos, merge=merge),
    description="Manage your task list for the current session",
)
