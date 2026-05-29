"""TUIState - TUI 状态管理器。

维护会话状态、加载状态、工具调用历史和布局配置。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 状态文件路径
STATE_DIR = Path.home() / ".nanohermes" / "tui"
STATE_FILE = STATE_DIR / "state.json"


@dataclass
class ToolCallRecord:
    """工具调用记录。
    
    Attributes:
        tool_name: 工具名称。
        status: 状态（start/running/success/error）。
        args: 工具参数。
        result: 工具结果。
        started_at: 开始时间戳。
        completed_at: 完成时间戳。
    """
    tool_name: str
    status: str = "start"
    args: dict[str, Any] = field(default_factory=dict)
    result: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0


@dataclass
class TUIState:
    """TUI 状态管理器。
    
    维护所有 TUI 状态变量。
    
    Attributes:
        running: TUI 是否正在运行。
        welcomed: 是否已显示欢迎消息。
        session_id: 当前会话 ID。
        loading: 是否正在加载（等待 Agent 响应）。
        tool_calls: 工具调用历史记录。
        layout: 布局配置。
        input_history: 输入历史记录。
    """
    running: bool = False
    welcomed: bool = False
    session_id: str = ""
    loading: bool = False
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    layout: dict[str, Any] = field(default_factory=lambda: {
        "show_tool_panel": True,
        "tool_panel_position": "right",
        "typing_speed": 10,  # 打字机速度（ms）
    })
    input_history: list[str] = field(default_factory=list)
    
    def add_tool_call(self, tool_name: str, args: dict[str, Any] | None = None) -> ToolCallRecord:
        """添加工具调用记录。
        
        Args:
            tool_name: 工具名称。
            args: 工具参数。
            
        Returns:
            新创建的工具调用记录。
        """
        import time
        record = ToolCallRecord(
            tool_name=tool_name,
            args=args or {},
            started_at=time.time(),
        )
        self.tool_calls.append(record)
        return record
    
    def update_tool_call(self, index: int, status: str, result: str = "") -> None:
        """更新工具调用状态。
        
        Args:
            index: 工具调用记录索引。
            status: 新状态。
            result: 工具结果。
        """
        import time
        if 0 <= index < len(self.tool_calls):
            self.tool_calls[index].status = status
            self.tool_calls[index].result = result
            if status in ("success", "error"):
                self.tool_calls[index].completed_at = time.time()
    
    def save(self) -> None:
        """保存状态到文件。"""
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            
            # 转换为可序列化格式
            state_dict = {
                "session_id": self.session_id,
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "status": tc.status,
                        "args": tc.args,
                        "result": tc.result,
                        "started_at": tc.started_at,
                        "completed_at": tc.completed_at,
                    }
                    for tc in self.tool_calls[-100:]  # 只保留最近 100 条
                ],
                "layout": self.layout,
                "input_history": self.input_history[-1000:],  # 只保留最近 1000 条
            }
            
            STATE_FILE.write_text(
                json.dumps(state_dict, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            logger.debug(f"状态已保存到 {STATE_FILE}")
            
        except Exception as e:
            logger.warning(f"保存状态失败: {e}", exc_info=True)
    
    def load(self) -> None:
        """从文件加载状态。"""
        if not STATE_FILE.exists():
            return
        
        try:
            state_dict = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            
            self.session_id = state_dict.get("session_id", "")
            self.layout = state_dict.get("layout", self.layout)
            self.input_history = state_dict.get("input_history", [])
            
            # 恢复工具调用记录
            self.tool_calls = [
                ToolCallRecord(
                    tool_name=tc["tool_name"],
                    status=tc["status"],
                    args=tc.get("args", {}),
                    result=tc.get("result", ""),
                    started_at=tc.get("started_at", 0.0),
                    completed_at=tc.get("completed_at", 0.0),
                )
                for tc in state_dict.get("tool_calls", [])
            ]
            
            logger.debug(f"状态已从 {STATE_FILE} 加载")
            
        except Exception as e:
            logger.warning(f"加载状态失败: {e}", exc_info=True)
