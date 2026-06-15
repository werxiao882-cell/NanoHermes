"""内置文件基础记忆提供者。

使用 MemoryStore 作为唯一数据源管理 MEMORY.md 和 USER.md。
重构前：自有读写逻辑（_add_entry, _replace_entry, _remove_entry, _atomic_write）。
重构后：全部委托给 MemoryStore，自身只负责生命周期和接口适配。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.memory.provider import MemoryProvider

logger = logging.getLogger(__name__)

MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375

MEMORY_TOOL_SCHEMA = {
    "name": "memory",
    "description": "Manage persistent memory across sessions. Add, replace, or remove memory entries.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "replace", "remove"],
                "description": "Operation to perform: add new entry, replace existing, or remove entry"
            },
            "target": {
                "type": "string",
                "enum": ["memory", "user"],
                "description": "Target file: 'memory' for MEMORY.md, 'user' for USER.md"
            },
            "content": {
                "type": "string",
                "description": "Content to add or replace with"
            },
            "search": {
                "type": "string",
                "description": "Search string to find entry for replace/remove operations"
            }
        },
        "required": ["action", "target", "content"]
    }
}


class FileMemoryProvider(MemoryProvider):
    """内置文件基础记忆提供者。

    委托 MemoryStore 执行所有记忆操作。
    构造函数接受可选的 MemoryStore 实例（依赖注入），
    如果未提供则自动创建（向后兼容）。
    """

    def __init__(self, hermes_home: str, store: Optional[Any] = None):
        self._hermes_home = Path(hermes_home)
        self._memory_dir = self._hermes_home / "memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)

        if store is not None:
            self._store = store
        else:
            from src.memory.memory_store import MemoryStore
            self._store = MemoryStore(self._memory_dir)

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def is_external(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """委托 MemoryStore.load_from_disk() 加载条目并捕获冻结快照。"""
        self._store.load_from_disk()

    def system_prompt_block(self) -> str:
        """返回冻结快照（不再每轮重读文件）。"""
        return self.prefetch("")

    def prefetch(self, query: str = "", **kwargs) -> str:
        """返回冻结快照。

        设计理由：
        系统提示使用冻结快照保证 Anthropic prompt caching 前缀稳定。
        不再每轮重读文件，避免前缀缓存失效。
        """
        parts: List[str] = []
        for target in ("memory", "user"):
            block = self._store.format_for_system_prompt(target)
            if block:
                parts.append(block)
        return "\n\n".join(parts)

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        pass

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [MEMORY_TOOL_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """委托 MemoryStore 处理 memory 工具调用。"""
        if tool_name != "memory":
            raise NotImplementedError(f"FileMemoryProvider does not handle tool {tool_name}")
        return self._handle_memory_action(args)

    def _handle_memory_action(self, args: Dict[str, Any]) -> str:
        """委托 MemoryStore 执行记忆操作。"""
        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content", "")

        if action == "add":
            result = self._store.add(target, content)
        elif action == "replace":
            search = args.get("search", "")
            result = self._store.replace(target, search, content)
        elif action == "remove":
            search = args.get("search", content)
            result = self._store.remove(target, search)
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

        return json.dumps(result, ensure_ascii=False)

    def add_entry(self, title: str, content: str, target: str = "memory") -> bool:
        """添加一条记忆（兼容接口）。"""
        entry = f"{title}: {content}"
        result = self._store.add(target, entry)
        return result.get("success", False)

    def on_session_end(self, messages: List[dict]) -> None:
        """会话结束时的钩子。

        实际的记忆提取由后台任务调度器通过 memory_flush_task 完成。
        此方法仅作为扩展点，供子类覆盖。

        Args:
            messages: 完整对话历史。
        """
        pass

    def shutdown(self) -> None:
        pass
