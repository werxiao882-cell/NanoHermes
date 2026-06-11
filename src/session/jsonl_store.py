"""JSONL 会话历史存储。

使用 JSONL (JSON Lines) 格式保存完整的会话历史记录。
每条消息一行 JSON，增量追加，不重复存储历史消息。

记录类型：
- session_start: 会话元数据（model, session_id, tools_schema）
- user: 用户消息
- assistant: 助手回复（含 reasoning, usage）
- tool_call: 工具调用（含 tool_name, arguments）
- tool_result: 工具结果（含 tool_call_id, content）

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

    每个会话一个 JSONL 文件，增量追加消息记录，不重复存储历史。

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
        """获取会话的 JSONL 文件路径。"""
        return self.base_dir / f"{session_id}.jsonl"

    def _append_record(self, session_id: str, record: dict[str, Any]) -> None:
        """追加一条记录到 JSONL 文件。"""
        file_path = self._get_file_path(session_id)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    def start_session(
        self,
        session_id: str,
        model: str,
        tools_schema: list[dict[str, Any]] | None = None,
    ) -> None:
        """记录会话开始，写入元数据和工具 schema。

        Args:
            session_id: 会话 ID。
            model: 使用的模型名称。
            tools_schema: 工具 schema 列表（只存一次）。
        """
        record = {
            "type": "session_start",
            "session_id": session_id,
            "model": model,
            "timestamp": time.time(),
        }
        if tools_schema:
            record["tools"] = tools_schema
        self._append_record(session_id, record)

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str | None = None,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        tool_name: str | None = None,
        tool_args: str | None = None,
        reasoning: str | None = None,
        usage: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tool_name: str | None = None,
        tool_args: str | dict | None = None,
    ) -> None:
        """追加一条消息到 JSONL 文件。

        Args:
            session_id: 会话 ID。
            role: 消息角色（user/assistant/tool_call/tool_result）。
            content: 消息内容。
            tool_calls: 工具调用列表。
            tool_call_id: 工具调用 ID（tool_result 时设置）。
            tool_name: 工具名称（tool_call/tool_result 时设置）。
            tool_args: 工具参数 JSON 字符串（tool_call 时设置）。
            reasoning: 推理内容。
            usage: token 用量。
            metadata: 额外元数据。
            tool_name: 工具名称（tool_call/tool_result 时设置）。
            tool_args: 工具参数（tool_call 时设置）。
        """
        record = {
            "type": role,
            "role": role,
            "timestamp": time.time(),
        }

        if content is not None:
            record["content"] = content
        if tool_calls:
            record["tool_calls"] = tool_calls
        if tool_call_id:
            record["tool_call_id"] = tool_call_id
        if tool_name:
            record["tool_name"] = tool_name
        if tool_args:
            record["tool_args"] = tool_args
        if reasoning:
            record["reasoning"] = reasoning
        if usage:
            record["usage"] = usage
        if metadata:
            record["metadata"] = metadata
        if tool_name:
            record["tool_name"] = tool_name
        if tool_args:
            record["tool_args"] = tool_args

        self._append_record(session_id, record)

    def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """从 JSONL 文件加载完整的会话历史。

        Args:
            session_id: 会话 ID。

        Returns:
            消息记录列表，按时间顺序排列（内部格式，含 type 字段）。
        """
        file_path = self._get_file_path(session_id)

        if not file_path.exists():
            return []

        messages = []
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # 使用 JSONDecoder 解析多个 JSON 对象（支持多行格式化 JSON）
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(content):
            # 跳过空白字符
            while idx < len(content) and content[idx].isspace():
                idx += 1
            if idx >= len(content):
                break
            
            try:
                obj, end_idx = decoder.raw_decode(content, idx)
                messages.append(obj)
                idx = end_idx
            except json.JSONDecodeError:
                # 跳过无法解析的部分
                idx += 1

        return messages

    def session_exists(self, session_id: str) -> bool:
        """检查会话的 JSONL 文件是否存在。"""
        return self._get_file_path(session_id).exists()

    def list_sessions(self) -> list[str]:
        """列出所有有 JSONL 文件的会话 ID。"""
        if not self.base_dir.exists():
            return []

        return [
            f.stem
            for f in self.base_dir.glob("*.jsonl")
            if f.is_file()
        ]

    def delete_session(self, session_id: str) -> bool:
        """删除会话的 JSONL 文件。"""
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def get_message_count(self, session_id: str) -> int:
        """获取会话的消息数量。"""
        return len(self.load_messages(session_id))
