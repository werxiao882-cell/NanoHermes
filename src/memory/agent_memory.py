"""Agent Memory Provider - Agent 级记忆。

支持三种作用域的记忆管理：
- Session Scope: 当前会话内的临时记忆
- Agent Scope: Agent 级别的持久记忆（跨会话）
- Team Scope: 团队/项目级别的共享记忆

设计理由：
- 不同作用域的记忆有不同的生命周期和访问模式
- Session 记忆随会话结束而归档
- Agent 记忆跨会话持久化
- Team 记忆在多个 Agent 间共享
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.memory.provider import MemoryProvider
from src.memory.memory_store import get_session_summary_path, get_agent_memory_path, get_team_memory_path

logger = logging.getLogger(__name__)


class AgentMemoryProvider(MemoryProvider):
    """Agent 级记忆提供者。

    支持多作用域记忆：
    - session: 会话级（临时，随会话结束）
    - agent: Agent 级（持久，跨会话）
    - team: 团队级（共享，跨 Agent）
    """

    def __init__(
        self,
        memory_dir: Optional[Path] = None,
        scope: str = "agent",
        agent_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ):
        self._memory_dir = memory_dir or Path.home() / ".nanohermes" / "memory"
        self._scope = scope  # session / agent / team
        self._agent_id = agent_id or "default"
        self._team_id = team_id
        self._session_id: str = ""
        self._memories: Dict[str, str] = {}
        self._initialized: bool = False

    @property
    def name(self) -> str:
        return f"agent-{self._scope}"

    @property
    def is_external(self) -> bool:
        return True

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        """初始化 Agent 记忆。

        根据作用域加载相应的记忆文件。
        """
        self._session_id = session_id
        self._memories = {}
        self._initialized = True

        try:
            memory_path = self._get_memory_path()
            if memory_path.exists():
                data = json.loads(memory_path.read_text(encoding="utf-8"))
                self._memories = data.get("memories", {})
                logger.info(
                    f"Agent memory loaded: scope={self._scope}, "
                    f"agent={self._agent_id}, {len(self._memories)} entries"
                )
        except Exception as e:
            logger.warning(f"Failed to load agent memory: {e}")

    def _get_memory_path(self) -> Path:
        """获取记忆文件路径。"""
        if self._scope == "session":
            return get_session_summary_path(self._session_id, self._memory_dir)
        elif self._scope == "agent":
            return get_agent_memory_path(self._agent_id, self._memory_dir)
        elif self._scope == "team":
            return get_team_memory_path(self._team_id or "default", self._memory_dir)
        else:
            raise ValueError(f"Unknown scope: {self._scope}")

    def system_prompt_block(self) -> str:
        """返回 Agent 记忆注入到系统提示。"""
        if not self._memories:
            return ""

        lines = [f"<agent-memory scope='{self._scope}'>"]
        for key, value in self._memories.items():
            lines.append(f"- {key}: {value}")
        lines.append("</agent-memory>")

        return "\n".join(lines)

    def prefetch(self, query: str, **kwargs) -> str:
        """预取相关记忆（简单关键词匹配）。"""
        if not self._memories:
            return ""

        query_lower = query.lower()
        relevant = {
            k: v for k, v in self._memories.items()
            if k.lower() in query_lower or any(word in v.lower() for word in query_lower.split())
        }

        if not relevant:
            return ""

        lines = [f"<relevant-memory scope='{self._scope}'>"]
        for key, value in relevant.items():
            lines.append(f"- {key}: {value}")
        lines.append("</relevant-memory>")

        return "\n".join(lines)

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """同步轮次数据（当前不自动提取，由工具调用管理）。"""
        pass

    def shutdown(self) -> None:
        """保存记忆。"""
        if self._memories:
            try:
                memory_path = self._get_memory_path()
                memory_path.parent.mkdir(parents=True, exist_ok=True)
                memory_path.write_text(
                    json.dumps({"memories": self._memories}, indent=2),
                    encoding="utf-8",
                )
                logger.info(f"Agent memory saved: {len(self._memories)} entries")
            except Exception as e:
                logger.warning(f"Failed to save agent memory: {e}")

    def add_memory(self, key: str, value: str) -> None:
        """添加记忆。"""
        self._memories[key] = value
        logger.debug(f"Memory added: {key}")

    def remove_memory(self, key: str) -> bool:
        """删除记忆。"""
        if key in self._memories:
            del self._memories[key]
            return True
        return False

    def get_memory(self, key: str) -> Optional[str]:
        """获取记忆。"""
        return self._memories.get(key)

    def list_memories(self) -> Dict[str, str]:
        """列出所有记忆。"""
        return dict(self._memories)

    def clear_memories(self) -> None:
        """清空所有记忆。"""
        self._memories.clear()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """提供 Agent 记忆管理工具。"""
        return [
            {
                "name": "agent_memory",
                "description": "Manage agent-level memory (cross-session persistent).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["add", "get", "list", "remove", "clear"],
                            "description": "Action to perform.",
                        },
                        "key": {
                            "type": "string",
                            "description": "Memory key (for add/get/remove).",
                        },
                        "value": {
                            "type": "string",
                            "description": "Memory value (for add).",
                        },
                    },
                    "required": ["action"],
                },
            }
        ]

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理 Agent 记忆工具调用。"""
        action = args.get("action", "")
        key = args.get("key", "")
        value = args.get("value", "")

        if action == "add" and key:
            self.add_memory(key, value)
            return json.dumps({"success": True, "action": "add", "key": key})
        elif action == "get" and key:
            val = self.get_memory(key)
            return json.dumps({"success": val is not None, "key": key, "value": val})
        elif action == "list":
            return json.dumps({"success": True, "memories": self.list_memories()})
        elif action == "remove" and key:
            removed = self.remove_memory(key)
            return json.dumps({"success": removed, "action": "remove", "key": key})
        elif action == "clear":
            self.clear_memories()
            return json.dumps({"success": True, "action": "clear"})
        else:
            return json.dumps({"error": f"Invalid action: {action}"})
