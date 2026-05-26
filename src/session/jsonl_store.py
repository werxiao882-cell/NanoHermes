"""JSONL 会话历史存储。

使用 JSONL (JSON Lines) 格式保存完整的会话历史记录，支持：
- 每条消息一行 JSON，便于追加和流式写入
- 完整的消息元数据（role, content, tool_calls, timestamp, reasoning）
- 会话恢复：从 JSONL 文件加载历史消息
- 与 SessionDB 配合使用：SQLite 用于搜索和统计，JSONL 用于完整历史

文件命名: {session_id}.jsonl
存储路径: ~/.nanohermes/sessions/{session_id}.jsonl
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class JsonlSessionStore:
    """JSONL 格式的会话历史存储。

    每个会话一个 JSONL 文件，支持追加写入和完整恢复。

    Attributes:
        base_dir: JSONL 文件存储的基础目录。
    """

    def __init__(self, base_dir: str | Path | None = None):
        """初始化 JSONL 存储。

        Args:
            base_dir: 基础目录，None 时使用 ~/.nanohermes/sessions/。
        """
        if base_dir is None:
            base_dir = Path.home() / ".nanohermes" / "sessions"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, session_id: str) -> Path:
        """获取会话的 JSONL 文件路径。

        Args:
            session_id: 会话 ID。

        Returns:
            JSONL 文件路径。
        """
        return self.base_dir / f"{session_id}.jsonl"

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        reasoning: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """追加一条消息到 JSONL 文件。

        Args:
            session_id: 会话 ID。
            role: 消息角色（user/assistant/system/tool）。
            content: 消息内容。
            tool_calls: 工具调用列表。
            tool_call_id: 工具调用 ID（tool 角色时设置）。
            reasoning: 推理内容（如果模型支持）。
            metadata: 额外元数据。
        """
        file_path = self._get_file_path(session_id)

        record = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
        }

        if tool_calls:
            record["tool_calls"] = tool_calls
        if tool_call_id:
            record["tool_call_id"] = tool_call_id
        if reasoning:
            record["reasoning"] = reasoning
        if metadata:
            record["metadata"] = metadata

        # 追加写入（JSONL 格式，每行一条 JSON）
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """从 JSONL 文件加载完整的会话历史。

        Args:
            session_id: 会话 ID。

        Returns:
            消息列表，按时间顺序排列。
        """
        file_path = self._get_file_path(session_id)

        if not file_path.exists():
            return []

        messages = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        messages.append(record)
                    except json.JSONDecodeError:
                        continue  # 跳过损坏的行

        return messages

    def session_exists(self, session_id: str) -> bool:
        """检查会话的 JSONL 文件是否存在。

        Args:
            session_id: 会话 ID。

        Returns:
            True 表示文件存在。
        """
        return self._get_file_path(session_id).exists()

    def list_sessions(self) -> list[str]:
        """列出所有有 JSONL 文件的会话 ID。

        Returns:
            会话 ID 列表。
        """
        if not self.base_dir.exists():
            return []

        return [
            f.stem
            for f in self.base_dir.glob("*.jsonl")
            if f.is_file()
        ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话的 JSONL 文件。

        Args:
            session_id: 会话 ID。

        Returns:
            True 表示删除成功，False 表示文件不存在。
        """
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_message_count(self, session_id: str) -> int:
        """获取会话的消息数量。

        Args:
            session_id: 会话 ID。

        Returns:
            消息数量。
        """
        file_path = self._get_file_path(session_id)
        if not file_path.exists():
            return 0

        count = 0
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
