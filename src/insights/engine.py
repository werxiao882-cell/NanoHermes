"""InsightsEngine - 洞察引擎。

查询会话数据生成完整报告：
- 概览（总会话数、总消息数、总 token、总成本）
- 模型分解
- 平台分解
- 工具使用排名
- 技能使用
- 活动趋势
- 顶部会话
- 成本估算
- 终端格式化输出
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# 成本估算
# ============================================================================

# 模型定价数据库（USD / 1M tokens）
# 来源：各提供商公开定价，可能随时间变化
PRICING_DATABASE: dict[str, dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25, "cache_write": 3.125},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.1875},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00, "cache_read": 5.00, "cache_write": 15.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50, "cache_read": 0.25, "cache_write": 0.75},
    "o1": {"input": 15.00, "output": 60.00, "cache_read": 7.50, "cache_write": 37.50},
    "o1-mini": {"input": 3.00, "output": 12.00, "cache_read": 1.50, "cache_write": 7.50},
    "o3-mini": {"input": 1.10, "output": 4.40, "cache_read": 0.55, "cache_write": 2.75},
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00, "cache_read": 0.08, "cache_write": 1.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_write": 18.75},
    # DashScope (通义千问)
    "qwen-turbo": {"input": 0.002, "output": 0.006, "cache_read": 0.001, "cache_write": 0.003},
    "qwen-plus": {"input": 0.004, "output": 0.012, "cache_read": 0.002, "cache_write": 0.006},
    "qwen-max": {"input": 0.02, "output": 0.06, "cache_read": 0.01, "cache_write": 0.03},
    "qwen-long": {"input": 0.0005, "output": 0.002, "cache_read": 0.00025, "cache_write": 0.001},
    # DeepSeek
    "deepseek-chat": {"input": 0.27, "output": 1.10, "cache_read": 0.07, "cache_write": 0.55},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19, "cache_read": 0.14, "cache_write": 1.10},
    # 通用默认（保守估计）
    "default": {"input": 3.00, "output": 10.00, "cache_read": 0.30, "cache_write": 3.75},
}


@dataclass
class TokenUsage:
    """Token 使用量。

    Attributes:
        input_tokens: 输入 token 数。
        output_tokens: 输出 token 数。
        cache_read_tokens: 缓存读取 token 数。
        cache_write_tokens: 缓存写入 token 数。
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0


@dataclass
class CostEstimate:
    """成本估算结果。

    Attributes:
        amount_usd: 估算成本（美元）。
        status: 估算状态（estimated/unknown）。
        breakdown: 成本明细。
    """
    amount_usd: float = 0.0
    status: str = "unknown"
    breakdown: dict[str, float] = field(default_factory=dict)


def estimate_cost(model: str, usage: TokenUsage, provider: str | None = None) -> CostEstimate:
    """估算 API 调用成本。

    设计理由：
    - 使用 per-1M-tokens 定价，除以 1_000_000 得到实际成本
    - 未知模型返回 0 成本 + unknown 状态
    - 缓存 token 成本通常低于常规 token

    Args:
        model: 模型名称（如 "gpt-4o", "qwen-plus"）。
        usage: Token 使用量。
        provider: 提供商名称（可选，用于定价查找）。

    Returns:
        CostEstimate 实例。
    """
    pricing = PRICING_DATABASE.get(model, PRICING_DATABASE.get("default"))

    if pricing is None or model not in PRICING_DATABASE:
        return CostEstimate(amount_usd=0.0, status="unknown")

    input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
    output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
    cache_read_cost = (usage.cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)
    cache_write_cost = (usage.cache_write_tokens / 1_000_000) * pricing.get("cache_write", 0)

    total = input_cost + output_cost + cache_read_cost + cache_write_cost

    return CostEstimate(
        amount_usd=total,
        status="estimated",
        breakdown={
            "input": input_cost,
            "output": output_cost,
            "cache_read": cache_read_cost,
            "cache_write": cache_write_cost,
        }
    )


# ============================================================================
# 洞察报告
# ============================================================================

@dataclass
class InsightsReport:
    """洞察报告。

    Attributes:
        days: 报告覆盖的天数。
        source_filter: 源过滤器（如 "local", "telegram"）。
        total_sessions: 总会话数。
        total_messages: 总消息数。
        total_tokens: 总 token 数。
        estimated_cost: 总估算成本 (USD)。
        model_breakdown: 模型使用分解。
        platform_breakdown: 平台使用分解。
        tool_ranking: 工具使用排名。
        skill_usage: 技能使用统计。
        daily_activity: 每日活动趋势。
        top_sessions: 顶部会话列表。
    """
    days: int = 30
    source_filter: str | None = None
    total_sessions: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    model_breakdown: list[dict[str, Any]] = field(default_factory=list)
    platform_breakdown: list[dict[str, Any]] = field(default_factory=list)
    tool_ranking: list[dict[str, Any]] = field(default_factory=list)
    skill_usage: list[dict[str, Any]] = field(default_factory=list)
    daily_activity: list[dict[str, Any]] = field(default_factory=list)
    top_sessions: list[dict[str, Any]] = field(default_factory=list)


# ============================================================================
# InsightsEngine
# ============================================================================

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

    def generate(self, days: int = 30, source: str | None = None) -> InsightsReport:
        """生成完整洞察报告。

        设计理由：
        - 收集所有原始数据后再计算各项指标
        - 空数据时返回空报告而非错误
        - 支持按源（platform）过滤

        Args:
            days: 报告覆盖天数（默认 30）。
            source: 源过滤器（可选）。

        Returns:
            InsightsReport 实例。
        """
        cutoff = time.time() - (days * 86400)

        # 收集原始数据
        sessions = self._get_sessions(cutoff, source)
        tool_usage = self._get_tool_usage(cutoff, source)
        skill_usage = self._get_skill_usage(cutoff, source)
        message_stats = self._get_message_stats(cutoff, source)

        if not sessions:
            return InsightsReport(
                days=days,
                source_filter=source,
            )

        return InsightsReport(
            days=days,
            source_filter=source,
            total_sessions=len(sessions),
            total_messages=message_stats.get("total_messages", 0),
            total_tokens=self._compute_total_tokens(sessions),
            estimated_cost=self._compute_total_cost(sessions),
            model_breakdown=self._compute_model_breakdown(sessions),
            platform_breakdown=self._compute_platform_breakdown(sessions),
            tool_ranking=self._compute_tool_ranking(tool_usage),
            skill_usage=self._compute_skill_usage(skill_usage),
            daily_activity=self._compute_activity_trend(sessions),
            top_sessions=self._compute_top_sessions(sessions),
        )

    # ---- 数据收集方法 ----

    def _get_sessions(self, cutoff: float, source: str | None) -> list[dict[str, Any]]:
        """获取指定时间范围内的会话列表。

        Args:
            cutoff: 时间戳下限。
            source: 源过滤器。

        Returns:
            会话列表。
        """
        if not self._db or not hasattr(self._db, "conn") or not self._db.conn:
            return []

        try:
            query = "SELECT * FROM sessions WHERE started_at >= ?"
            params: list = [cutoff]

            if source:
                query += " AND source = ?"
                params.append(source)

            query += " ORDER BY started_at DESC"

            cursor = self._db.conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def _get_tool_usage(self, cutoff: float, source: str | None) -> list[dict[str, Any]]:
        """获取工具使用记录。

        从 messages 表中提取 tool_call 类型的消息。

        Args:
            cutoff: 时间戳下限。
            source: 源过滤器。

        Returns:
            工具使用记录列表。
        """
        if not self._db or not hasattr(self._db, "conn") or not self._db.conn:
            return []

        try:
            query = """
                SELECT m.tool_name, m.session_id, m.timestamp
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.tool_name IS NOT NULL
                  AND m.timestamp >= ?
            """
            params: list = [cutoff]

            if source:
                query += " AND s.source = ?"
                params.append(source)

            query += " ORDER BY m.timestamp DESC"

            cursor = self._db.conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []

    def _get_skill_usage(self, cutoff: float, source: str | None) -> list[dict[str, Any]]:
        """获取技能使用记录。

        从 messages 表中提取包含 skill 引用的消息。

        Args:
            cutoff: 时间戳下限。
            source: 源过滤器。

        Returns:
            技能使用记录列表。
        """
        if not self._db or not hasattr(self._db, "conn") or not self._db.conn:
            return []

        try:
            # 查找消息内容中包含 "skill" 引用的记录
            query = """
                SELECT m.content, m.session_id, m.timestamp
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.content LIKE '%skill%'
                  AND m.timestamp >= ?
                  AND m.role = 'assistant'
            """
            params: list = [cutoff]

            if source:
                query += " AND s.source = ?"
                params.append(source)

            cursor = self._db.conn.execute(query, params)
            results = []
            for row in cursor.fetchall():
                row_dict = dict(row)
                # 尝试从内容中提取技能名称
                results.append(row_dict)
            return results
        except Exception:
            return []

    def _get_message_stats(self, cutoff: float, source: str | None) -> dict[str, Any]:
        """获取消息统计信息。

        Args:
            cutoff: 时间戳下限。
            source: 源过滤器。

        Returns:
            包含 total_messages, total_tokens 等的字典。
        """
        if not self._db or not hasattr(self._db, "conn") or not self._db.conn:
            return {"total_messages": 0, "total_tokens": 0}

        try:
            query = """
                SELECT COUNT(*) as total_messages,
                       COALESCE(SUM(m.token_count), 0) as total_tokens
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE m.timestamp >= ?
            """
            params: list = [cutoff]

            if source:
                query += " AND s.source = ?"
                params.append(source)

            cursor = self._db.conn.execute(query, params)
            row = cursor.fetchone()
            if row:
                return {
                    "total_messages": row["total_messages"],
                    "total_tokens": row["total_tokens"],
                }
        except Exception:
            pass

        return {"total_messages": 0, "total_tokens": 0}

    # ---- 计算方法 ----

    def _compute_total_tokens(self, sessions: list[dict]) -> int:
        """计算总 token 数。"""
        return sum(
            s.get("input_tokens", 0) + s.get("output_tokens", 0) +
            s.get("cache_read_tokens", 0) + s.get("cache_write_tokens", 0)
            for s in sessions
        )

    def _compute_total_cost(self, sessions: list[dict]) -> float:
        """计算总估算成本。

        优先使用数据库中已有的 estimated_cost_usd，
        如果没有则根据 token 使用量重新估算。
        """
        total = 0.0
        for s in sessions:
            cost = s.get("estimated_cost_usd")
            if cost is not None and cost > 0:
                total += cost
            else:
                model = s.get("model", "")
                usage = TokenUsage(
                    input_tokens=s.get("input_tokens", 0),
                    output_tokens=s.get("output_tokens", 0),
                    cache_read_tokens=s.get("cache_read_tokens", 0),
                    cache_write_tokens=s.get("cache_write_tokens", 0),
                )
                estimate = estimate_cost(model, usage)
                total += estimate.amount_usd
        return round(total, 4)

    def _compute_model_breakdown(self, sessions: list[dict]) -> list[dict[str, Any]]:
        """计算模型使用分解。

        按模型分组，统计会话数、token 数、成本。

        Returns:
            模型分解列表，按会话数降序排列。
        """
        model_data: dict[str, dict] = defaultdict(lambda: {
            "sessions": 0, "tokens": 0, "cost": 0.0
        })

        for s in sessions:
            model = s.get("model", "unknown")
            model_data[model]["sessions"] += 1
            model_data[model]["tokens"] += (
                s.get("input_tokens", 0) + s.get("output_tokens", 0)
            )
            cost = s.get("estimated_cost_usd")
            if cost is not None:
                model_data[model]["cost"] += cost

        result = []
        for model, data in sorted(model_data.items(), key=lambda x: x[1]["sessions"], reverse=True):
            result.append({
                "model": model,
                "sessions": data["sessions"],
                "tokens": data["tokens"],
                "cost": round(data["cost"], 4),
            })

        return result

    def _compute_platform_breakdown(self, sessions: list[dict]) -> list[dict[str, Any]]:
        """计算平台使用分解。

        按 source（platform）分组，统计会话数、消息数。

        Returns:
            平台分解列表，按会话数降序排列。
        """
        platform_data: dict[str, dict] = defaultdict(lambda: {
            "sessions": 0, "messages": 0
        })

        for s in sessions:
            source = s.get("source", "unknown")
            platform_data[source]["sessions"] += 1
            platform_data[source]["messages"] += s.get("message_count", 0)

        result = []
        for platform, data in sorted(platform_data.items(), key=lambda x: x[1]["sessions"], reverse=True):
            result.append({
                "platform": platform,
                "sessions": data["sessions"],
                "messages": data["messages"],
            })

        return result

    def _compute_tool_ranking(self, tool_usage: list[dict]) -> list[dict[str, Any]]:
        """计算工具使用排名。

        Returns:
            工具使用排名列表，按调用次数降序排列。
        """
        if not tool_usage:
            return []

        counter = Counter(r["tool_name"] for r in tool_usage if r.get("tool_name"))
        result = []
        for tool_name, count in counter.most_common():
            result.append({
                "tool": tool_name,
                "calls": count,
            })

        return result

    def _compute_skill_usage(self, skill_records: list[dict]) -> list[dict[str, Any]]:
        """计算技能使用统计。

        Returns:
            技能使用列表。
        """
        if not skill_records:
            return []

        # 简单统计：统计提及技能的会话数
        session_skills: dict[str, int] = defaultdict(int)
        for record in skill_records:
            session_id = record.get("session_id", "")
            content = record.get("content", "")

            # 尝试提取技能名称（简单匹配）
            if "skill" in content.lower():
                session_skills[session_id] = session_skills.get(session_id, 0) + 1

        return [
            {"session_id": sid, "skill_mentions": count}
            for sid, count in sorted(session_skills.items(), key=lambda x: x[1], reverse=True)[:20]
        ]

    def _compute_activity_trend(self, sessions: list[dict]) -> list[dict[str, Any]]:
        """计算每日活动趋势。

        按日期分组，统计每日会话数、消息数、token 数。

        Returns:
            每日活动列表，按日期升序排列。
        """
        from datetime import datetime, timezone

        daily: dict[str, dict] = defaultdict(lambda: {
            "sessions": 0, "messages": 0, "tokens": 0
        })

        for s in sessions:
            started = s.get("started_at", 0)
            if started:
                dt = datetime.fromtimestamp(started, tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
                daily[date_str]["sessions"] += 1
                daily[date_str]["messages"] += s.get("message_count", 0)
                daily[date_str]["tokens"] += (
                    s.get("input_tokens", 0) + s.get("output_tokens", 0)
                )

        return [
            {"date": date, **data}
            for date, data in sorted(daily.items())
        ]

    def _compute_top_sessions(self, sessions: list[dict]) -> list[dict[str, Any]]:
        """计算顶部会话（按 token 使用量排序）。

        Returns:
            顶部会话列表。
        """
        scored = []
        for s in sessions:
            total_tokens = (
                s.get("input_tokens", 0) + s.get("output_tokens", 0) +
                s.get("cache_read_tokens", 0) + s.get("cache_write_tokens", 0)
            )
            scored.append({
                "session_id": s.get("id", ""),
                "title": s.get("title", ""),
                "model": s.get("model", ""),
                "tokens": total_tokens,
                "messages": s.get("message_count", 0),
                "started_at": s.get("started_at", 0),
                "cost": s.get("estimated_cost_usd", 0.0),
            })

        scored.sort(key=lambda x: x["tokens"], reverse=True)
        return scored[:10]

    # ---- 格式化方法 ----

    def format_terminal(self, report: InsightsReport) -> str:
        """将报告格式化为终端可读的文本。

        Args:
            report: InsightsReport 实例。

        Returns:
            格式化的终端输出字符串。
        """
        lines = ["## 洞察报告"]
        lines.append(f"覆盖天数: {report.days} 天")
        if report.source_filter:
            lines.append(f"源过滤: {report.source_filter}")
        lines.append("")

        # 概览
        lines.append("## 概览")
        lines.append(f"会话数: {report.total_sessions}")
        lines.append(f"消息数: {report.total_messages}")
        lines.append(f"Token: {self._format_compact(report.total_tokens)}")
        lines.append(f"成本: ${report.estimated_cost:.4f}")
        lines.append("")

        # 模型分解
        if report.model_breakdown:
            lines.append("## 模型使用")
            for m in report.model_breakdown:
                lines.append(f"  {m['model']}: {m['sessions']} 会话, "
                             f"{self._format_compact(m['tokens'])} tokens")
            lines.append("")

        # 平台分解
        if report.platform_breakdown:
            lines.append("## 平台分布")
            for p in report.platform_breakdown:
                lines.append(f"  {p['platform']}: {p['sessions']} 会话, "
                             f"{p['messages']} 消息")
            lines.append("")

        # 工具排名
        if report.tool_ranking:
            lines.append("## 工具使用排名")
            for t in report.tool_ranking[:10]:
                lines.append(f"  {t['tool']}: {t['calls']} 次调用")
            lines.append("")

        # 活动趋势
        if report.daily_activity:
            lines.append("## 每日活动")
            values = [d["sessions"] for d in report.daily_activity]
            lines.append(self._format_bar_chart(values))
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_compact(number: int) -> str:
        """格式化大数字为紧凑形式。

        Args:
            number: 数字。

        Returns:
            紧凑字符串（如 "1.2M", "3.4K"）。
        """
        if number >= 1_000_000:
            return f"{number / 1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.1f}K"
        return str(number)

    @staticmethod
    def _format_bar_chart(values: list[int], max_width: int = 20) -> str:
        """格式化条形图。

        Args:
            values: 数值列表。
            max_width: 最大条形宽度。

        Returns:
            条形图字符串。
        """
        if not values:
            return ""

        peak = max(values) if values else 1
        if peak == 0:
            peak = 1

        bars = []
        for v in values:
            width = max(1, int(v / peak * max_width))
            bars.append("█" * width)

        return "\n".join(bars)
