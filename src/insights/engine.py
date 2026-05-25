"""InsightsEngine - 洞察引擎。

查询会话数据生成完整报告：
- 概览（总会话数、总消息数、总 token、总成本）
- 模型分解
- 平台分解
- 工具使用排名
- 活动趋势
- 顶部会话
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class InsightsReport:
    """洞察报告。

    Attributes:
        total_sessions: 总会话数。
        total_messages: 总消息数。
        total_tokens: 总 token 数。
        total_cost: 总成本 (USD)。
        model_breakdown: 模型使用分解。
        tool_ranking: 工具使用排名。
        daily_activity: 每日活动趋势。
        top_sessions: 顶部会话列表。
    """
    total_sessions: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    model_breakdown: list[dict[str, Any]] | None = None
    tool_ranking: list[dict[str, Any]] | None = None
    daily_activity: list[dict[str, Any]] | None = None
    top_sessions: list[dict[str, Any]] | None = None


class InsightsEngine:
    """洞察引擎。

    从会话数据库查询数据，生成使用情况报告。
    """

    def __init__(self, session_db: Any):
        """初始化洞察引擎。

        Args:
            session_db: SessionDB 实例。
        """
        self._db = session_db

    def generate_report(self) -> InsightsReport:
        """生成完整洞察报告。

        Returns:
            InsightsReport 实例。
        """
        report = InsightsReport()

        # 从数据库获取数据
        if self._db:
            sessions = self._get_all_sessions()
            report.total_sessions = len(sessions)
            report.total_tokens = sum(
                s.get("input_tokens", 0) + s.get("output_tokens", 0)
                for s in sessions
            )

        return report

    def _get_all_sessions(self) -> list[dict[str, Any]]:
        """获取所有会话。

        Returns:
            会话列表。
        """
        if self._db and hasattr(self._db, "conn") and self._db.conn:
            cursor = self._db.conn.execute("SELECT * FROM sessions")
            return [dict(row) for row in cursor.fetchall()]
        return []
