"""内置文件基础记忆提供者。

使用 MEMORY.md 和 USER.md 文件存储记忆，支持 add/replace/remove 操作。
- MEMORY.md: Agent 的持久记忆（用户偏好、环境细节、工具经验）
- USER.md: 用户画像（角色、背景、习惯）
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from src.memory.provider import MemoryProvider

logger = logging.getLogger(__name__)

# 字符数限制
MEMORY_CHAR_LIMIT = 2200
USER_CHAR_LIMIT = 1375

# memory 工具 schema
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

    使用 Markdown 文件存储记忆，支持 add/replace/remove 操作。
    使用原子写入（临时文件 + rename）防止并发丢失。
    """

    def __init__(self, hermes_home: str):
        """初始化文件记忆提供者。

        Args:
            hermes_home: NanoHermes 主目录路径。
        """
        self._hermes_home = Path(hermes_home)
        self._memory_dir = self._hermes_home / "memory"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self._memory_path = self._memory_dir / "MEMORY.md"
        self._user_path = self._memory_dir / "USER.md"

    @property
    def name(self) -> str:
        return "builtin"

    @property
    def is_external(self) -> bool:
        """内置提供者不是外部提供者。"""
        return False

    def is_available(self) -> bool:
        """文件提供者始终可用。"""
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """确保记忆文件存在。

        Args:
            session_id: 当前会话 ID（未使用，但符合接口要求）。
            **kwargs: 可选参数。
        """
        if not self._memory_path.exists():
            self._memory_path.write_text("# Memory\n\n", encoding="utf-8")
            logger.debug(f"Created MEMORY.md at {self._memory_path}")

        if not self._user_path.exists():
            self._user_path.write_text("# User Profile\n\n", encoding="utf-8")
            logger.debug(f"Created USER.md at {self._user_path}")

    def system_prompt_block(self) -> str:
        """返回记忆内容作为系统提示块。"""
        return self.prefetch("")

    def prefetch(self, query: str = "", **kwargs) -> str:
        """读取 MEMORY.md 和 USER.md 内容。

        Args:
            query: 用户消息（未使用，文件提供者返回全部内容）。
            **kwargs: 可选参数。

        Returns:
            格式化的记忆上下文文本。
        """
        context_parts: List[str] = []

        # 读取 MEMORY.md
        if self._memory_path.exists():
            memory_content = self._memory_path.read_text(encoding="utf-8").strip()
            if memory_content:
                # 应用字符数限制
                if len(memory_content) > MEMORY_CHAR_LIMIT:
                    memory_content = memory_content[:MEMORY_CHAR_LIMIT]
                context_parts.append(f"## Memory\n\n{memory_content}")

        # 读取 USER.md
        if self._user_path.exists():
            user_content = self._user_path.read_text(encoding="utf-8").strip()
            if user_content:
                # 应用字符数限制
                if len(user_content) > USER_CHAR_LIMIT:
                    user_content = user_content[:USER_CHAR_LIMIT]
                context_parts.append(f"## User Profile\n\n{user_content}")

        return "\n\n".join(context_parts)

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """同步对话内容（实际提取由 memory 工具调用完成）。

        Args:
            user_content: 用户消息内容。
            assistant_content: 助手回复内容。
            **kwargs: 可选参数。
        """
        # 实际记忆提取由 Agent 通过 memory 工具调用完成
        pass

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回 memory 工具 schema。"""
        return [MEMORY_TOOL_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理 memory 工具调用。

        Args:
            tool_name: 工具名称（应为 'memory'）。
            args: 工具参数（action, target, content, search）。
            **kwargs: 可选参数。

        Returns:
            执行结果的 JSON 字符串。
        """
        if tool_name == "memory":
            return self._handle_memory_action(args)
        raise NotImplementedError(f"FileMemoryProvider does not handle tool {tool_name}")

    def _handle_memory_action(self, args: Dict[str, Any]) -> str:
        """处理记忆操作（add/replace/remove）。

        Args:
            args: 操作参数。

        Returns:
            执行结果的 JSON 字符串。
        """
        action = args.get("action", "")
        target = args.get("target", "memory")
        content = args.get("content", "")

        file_path = self._user_path if target == "user" else self._memory_path

        # 读取当前内容
        if file_path.exists():
            file_content = file_path.read_text(encoding="utf-8")
        else:
            file_content = "# Memory\n\n" if target == "memory" else "# User Profile\n\n"

        # 执行操作
        if action == "add":
            file_content = self._add_entry(file_content, content)
        elif action == "replace":
            search = args.get("search", "")
            file_content = self._replace_entry(file_content, search, content)
        elif action == "remove":
            search = args.get("search", content)
            file_content = self._remove_entry(file_content, search)
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})

        # 原子写入（临时文件 + rename）
        self._atomic_write(file_path, file_content)

        return json.dumps({"success": True})

    def _add_entry(self, content: str, entry: str) -> str:
        """添加记忆条目。

        Args:
            content: 当前文件内容。
            entry: 要添加的条目。

        Returns:
            更新后的文件内容。
        """
        # 确保以换行结尾
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"- {entry}\n"
        return content

    def add_entry(self, title: str, content: str, target: str = "memory") -> bool:
        """添加一条记忆到文件。

        Args:
            title: 记忆标题/标签。
            content: 记忆内容。
            target: 目标文件（'memory' 或 'user'）。

        Returns:
            是否成功添加。
        """
        file_path = self._user_path if target == "user" else self._memory_path

        if file_path.exists():
            file_content = file_path.read_text(encoding="utf-8")
        else:
            file_content = "# Memory\n\n" if target == "memory" else "# User Profile\n\n"

        entry = f"{title}: {content}"
        file_content = self._add_entry(file_content, entry)
        self._atomic_write(file_path, file_content)
        return True

    def _replace_entry(self, content: str, search: str, new_entry: str) -> str:
        """替换记忆条目。

        Args:
            content: 当前文件内容。
            search: 搜索字符串，用于匹配要替换的条目。
            new_entry: 新条目内容。

        Returns:
            更新后的文件内容。
        """
        lines = content.split("\n")
        new_lines = []
        replaced = False

        for line in lines:
            if search and search in line and line.strip().startswith("-"):
                new_lines.append(f"- {new_entry}")
                replaced = True
            else:
                new_lines.append(line)

        if not replaced:
            # 如果没有找到匹配项，作为新条目添加
            return self._add_entry(content, new_entry)

        return "\n".join(new_lines)

    def _remove_entry(self, content: str, search: str) -> str:
        """删除记忆条目。

        Args:
            content: 当前文件内容。
            search: 搜索字符串，用于匹配要删除的条目。

        Returns:
            更新后的文件内容。
        """
        lines = content.split("\n")
        new_lines = []

        for line in lines:
            # 只删除以 '-' 开头且包含搜索字符串的行
            if search and search in line and line.strip().startswith("-"):
                continue  # 删除该行
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def _atomic_write(self, file_path: Path, content: str) -> None:
        """原子写入文件（临时文件 + replace）。

        Args:
            file_path: 目标文件路径。
            content: 要写入的内容。
        """
        tmp_path = file_path.with_suffix(".tmp")
        tmp_path.write_text(content, encoding="utf-8")
        # 使用 replace 而非 rename，因为 Windows 上 rename 在目标存在时会失败
        tmp_path.replace(file_path)

    def shutdown(self) -> None:
        """关闭时清理（文件提供者无需特殊清理）。"""
        pass
