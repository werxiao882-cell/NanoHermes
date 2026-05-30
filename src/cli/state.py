"""TUIState - TUI 状态管理器。

维护会话状态、加载状态、工具调用历史和布局配置。
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_DIR = Path.home() / ".nanohermes" / "tui"
STATE_FILE = STATE_DIR / "state.json"


@dataclass
class ToolCallRecord:
    tool_name: str
    status: str = "start"
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class TUIState:
    running: bool = False
    welcomed: bool = False
    session_id: str = ""
    loading: bool = False
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=lambda: {
        "show_tool_panel": True,
        "tool_panel_position": "right",
        "typing_speed": 10,
    })
    input_history: list[str] = field(default_factory=list)

    def add_tool_call(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolCallRecord:
        record = ToolCallRecord(
            tool_name=tool_name,
            args=args or {},
            started_at=time.time(),
        )
        self.tool_calls.append(record)
        return record

    def update_tool_call(self, index: int, status: str, result: str = "") -> None:
        if 0 <= index < len(self.tool_calls):
            self.tool_calls[index].status = status
            self.tool_calls[index].result = result
            if status in ("success", "error"):
                self.tool_calls[index].completed_at = time.time()

    def save(self) -> None:
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            state_dict = {
                "session_id": self.session_id,
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name, "status": tc.status,
                        "args": tc.args, "result": tc.result,
                        "started_at": tc.started_at, "completed_at": tc.completed_at,
                    }
                    for tc in self.tool_calls[-100:]
                ],
                "layout": self.layout,
                "input_history": self.input_history[-1000:],
            }
            STATE_FILE.write_text(
                json.dumps(state_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"状态已保存到 {STATE_FILE}")
        except Exception as e:
            logger.warning(f"保存状态失败: {e}", exc_info=True)

    def load(self) -> None:
        if not STATE_FILE.exists():
            return
        try:
            state_dict = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            self.session_id = state_dict.get("session_id", "")
            self.layout = state_dict.get("layout", self.layout)
            self.input_history = state_dict.get("input_history", [])
            self.tool_calls = [
                ToolCallRecord(
                    tool_name=tc["tool_name"], status=tc["status"],
                    args=tc.get("args", {}), result=tc.get("result", ""),
                    started_at=tc.get("started_at", 0.0),
                    completed_at=tc.get("completed_at", 0.0),
                )
                for tc in state_dict.get("tool_calls", [])
            ]
            logger.debug(f"状态已从 {STATE_FILE} 加载")
        except Exception as e:
            logger.warning(f"加载状态失败: {e}", exc_info=True)
