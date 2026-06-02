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
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ─────────────────────────────────────────────
# 定价数据库（USD / 1M tokens）
# ─────────────────────────────────────────────
PRICING_DATABASE: dict[str, dict[str, float]] = {
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0, "cache_read": 1.5, "cache_write": 18.75},
    "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
    "claude-3-5-haiku-20241022": {"input": 0.8, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25, "cache_read": 0.025, "cache_write": 0.3},
    # OpenAI
    "gpt-4o": {"input": 2.5, "output": 10.0, "cache_read": 1.25, "cache_write": 2.5},
    "gpt-4o-mini": {"input": 0.15, "output": 0.6, "cache_read": 0.075, "cache_write": 0.15},
    "o1": {"input": 15.0, "output": 60.0, "cache_read": 0.0, "cache_write": 0.0},
    "o1-mini": {"input": 1.1, "output": 4.4, "cache_read": 0.0, "cache_write": 0.0},
    "o3": {"input": 10.0, "output": 40.0, "cache_read": 0.0, "cache_write": 0.0},
    "o3-mini": {"input": 1.1, "output": 4.4, "cache_read": 0.0, "cache_write": 0.0},
    # Google
    "gemini-2.5-pro": {"input": 1.25, "output": 10.0, "cache_read": 0.31, "cache_write": 0.31},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.6, "cache_read": 0.0375, "cache_write": 0.0375},
    "gemini-2.0-flash": {"input": 0.1, "output": 0.4, "cache_read": 0.025, "cache_write": 0.025},
    # DeepSeek
    "deepseek-chat": {"input": 0.27, "output": 1.1, "cache_read": 0.07, "cache_write": 0.28},
    # Mistral
    "mistral-large-2": {"input": 2.0, "output": 6.0, "cache_read": 0.0, "cache_write": 0.0},
    # Fallback
    "default": {"input": 3.0, "output": 15.0, "cache_read": 0.3, "cache_write": 3.75},
}


@dataclass
class InsightsReport:
    """洞察报告。

    Attributes:
        total_sessions: 总会话数。
        total_messages: 总消息数。
        total_tokens: 总 token 数。
        total_cost: 总成本 (USD)。
        model_breakdown: 模型使用分解。
        platform_breakdown: 平台使用分解。
        tool_ranking: 工具使用排名。
        skill_usage: 技能使用统计。
        daily_activity: 每日活动趋势。
        top_sessions: 顶部会话列表。
        message_stats: 消息统计。
    """
    total_sessions: int = 0
    total_messages: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    model_breakdown: list[dict[str, Any]] = field(default_factory=list)
    platform_breakdown: list[dict[str, Any]] = field(default_factory=list)
    tool_ranking: list[dict[str, Any]] = field(default_factory=list)
    skill_usage: list[dict[str, Any]] = field(default_factory=list)
    daily_activity: list[dict[str, Any]] = field(default_factory=list)
    top_sessions: list[dict[str, Any]] = field(default_factory=list)
    message_stats: dict[str, Any] = field(default_factory=dict)

    def format_terminal(self, width: int = 80) -> str:
        """格式化为终端输出。

        Args:
            width: 终端宽度。

        Returns:
            格式化的终端字符串。
        """
        return format_terminal(self, width)


# ─────────────────────────────────────────────
# InsightsEngine 类
# ─────────────────────────────────────────────
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

    # ── 公共 API ──

    def generate_report(
        self,
        *,
        source: str | None = None,
        limit: int | None = None,
        include_cost: bool = True,
    ) -> InsightsReport:
        """生成完整洞察报告。

        Args:
            source: 按来源过滤（如 "claude", "openai"）。
            limit: 限制分析的会话数量。
            include_cost: 是否包含成本估算。

        Returns:
            InsightsReport 实例。
        """
        report = InsightsReport()
        sessions = self.get_sessions(source=source, limit=limit)

        if not sessions:
            return report

        # 概览
        report.total_sessions = len(sessions)
        report.total_messages = sum(s.get("message_count", 0) for s in sessions)
        report.total_tokens = sum(
            s.get("input_tokens", 0) + s.get("output_tokens", 0)
            + s.get("cache_read_tokens", 0) + s.get("cache_write_tokens", 0)
            for s in sessions
        )

        if include_cost:
            report.total_cost = self._compute_total_cost(sessions)

        # 分解
        report.model_breakdown = self.compute_model_breakdown(sessions)
        report.platform_breakdown = self.compute_platform_breakdown(sessions)
        report.tool_ranking = self.compute_tool_ranking(sessions)
        report.skill_usage = self.compute_skill_usage(sessions)
        report.daily_activity = self.compute_activity_trend(sessions)
        report.top_sessions = self.compute_top_sessions(sessions)
        report.message_stats = self.get_message_stats(sessions)

        return report

    def get_sessions(
        self,
        *,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """获取会话列表。

        Args:
            source: 按来源过滤。
            limit: 限制数量。

        Returns:
            会话列表。
        """
        sessions = self._get_all_sessions()

        if source:
            sessions = [s for s in sessions if s.get("model", "").lower().startswith(source.lower())]

        if limit:
            sessions = sessions[:limit]

        return sessions

    def get_tool_usage(self, sessions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """获取工具使用统计。

        Args:
            sessions: 会话列表。如果为 None 则获取所有。

        Returns:
            工具使用排名列表。
        """
        if sessions is None:
            sessions = self.get_sessions()
        return self.compute_tool_ranking(sessions)

    def get_skill_usage(self, sessions: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """获取技能使用统计。

        Args:
            sessions: 会话列表。

        Returns:
            技能使用列表。
        """
        if sessions is None:
            sessions = self.get_sessions()
        return self.compute_skill_usage(sessions)

    def get_message_stats(self, sessions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """获取消息统计。

        Args:
            sessions: 会话列表。

        Returns:
            消息统计数据。
        """
        if sessions is None:
            sessions = self.get_sessions()
        return self._compute_message_stats(sessions)

    # ── 计算方法 ──

    def compute_overview(self, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """计算概览数据。

        Args:
            sessions: 会话列表。

        Returns:
            概览数据字典。
        """
        total_tokens = sum(
            s.get("input_tokens", 0) + s.get("output_tokens", 0)
            + s.get("cache_read_tokens", 0) + s.get("cache_write_tokens", 0)
            for s in sessions
        )
        total_cost = self._compute_total_cost(sessions)

        return {
            "total_sessions": len(sessions),
            "total_messages": sum(s.get("message_count", 0) for s in sessions),
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 4),
            "avg_tokens_per_session": round(total_tokens / max(len(sessions), 1)),
            "avg_cost_per_session": round(total_cost / max(len(sessions), 1), 4),
        }

    def compute_model_breakdown(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """计算模型使用分解。

        Args:
            sessions: 会话列表。

        Returns:
            模型分解列表，按 token 数降序。
        """
        model_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"sessions": 0, "tokens": 0, "cost": 0.0, "messages": 0}
        )

        for s in sessions:
            model = s.get("model", "unknown")
            input_tokens = s.get("input_tokens", 0)
            output_tokens = s.get("output_tokens", 0)
            cache_read = s.get("cache_read_tokens", 0)
            cache_write = s.get("cache_write_tokens", 0)
            total = input_tokens + output_tokens + cache_read + cache_write

            model_data[model]["sessions"] += 1
            model_data[model]["tokens"] += total
            model_data[model]["messages"] += s.get("message_count", 0)
            model_data[model]["cost"] += estimate_cost(model, input_tokens, output_tokens, cache_read, cache_write)

        breakdown = []
        for model, data in sorted(model_data.items(), key=lambda x: x[1]["tokens"], reverse=True):
            breakdown.append({
                "model": model,
                "sessions": data["sessions"],
                "messages": data["messages"],
                "tokens": data["tokens"],
                "cost": round(data["cost"], 4),
            })

        return breakdown

    def compute_platform_breakdown(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """计算平台使用分解。

        Args:
            sessions: 会话列表。

        Returns:
            平台分解列表，按 token 数降序。
        """
        platform_map = {
            "claude": "Anthropic",
            "gpt": "OpenAI",
            "o1": "OpenAI",
            "o3": "OpenAI",
            "gemini": "Google",
            "deepseek": "DeepSeek",
            "mistral": "Mistral",
        }

        platform_data: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"sessions": 0, "tokens": 0, "cost": 0.0, "models": set()}
        )

        for s in sessions:
            model = s.get("model", "unknown").lower()
            platform = "Unknown"
            for prefix, pname in platform_map.items():
                if model.startswith(prefix):
                    platform = pname
                    break

            input_tokens = s.get("input_tokens", 0)
            output_tokens = s.get("output_tokens", 0)
            cache_read = s.get("cache_read_tokens", 0)
            cache_write = s.get("cache_write_tokens", 0)
            total = input_tokens + output_tokens + cache_read + cache_write

            platform_data[platform]["sessions"] += 1
            platform_data[platform]["tokens"] += total
            platform_data[platform]["models"].add(s.get("model", "unknown"))
            platform_data[platform]["cost"] += estimate_cost(model, input_tokens, output_tokens, cache_read, cache_write)

        breakdown = []
        for platform, data in sorted(platform_data.items(), key=lambda x: x[1]["tokens"], reverse=True):
            breakdown.append({
                "platform": platform,
                "sessions": data["sessions"],
                "tokens": data["tokens"],
                "cost": round(data["cost"], 4),
                "model_count": len(data["models"]),
            })

        return breakdown

    def compute_tool_ranking(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """计算工具使用排名。

        Args:
            sessions: 会话列表。

        Returns:
            工具排名列表，按使用次数降序。
        """
        tool_counter: Counter = Counter()

        for s in sessions:
            tool_calls = s.get("tool_calls", [])
            if isinstance(tool_calls, str):
                try:
                    tool_calls = json.loads(tool_calls)
                except (json.JSONDecodeError, TypeError):
                    tool_calls = []

            for tc in tool_calls:
                if isinstance(tc, dict):
                    name = tc.get("name", tc.get("tool_name", "unknown"))
                elif isinstance(tc, str):
                    name = tc
                else:
                    continue
                tool_counter[name] += 1

        total_uses = sum(tool_counter.values())
        ranking = []
        for rank, (tool, count) in enumerate(tool_counter.most_common(), 1):
            ranking.append({
                "rank": rank,
                "tool": tool,
                "count": count,
                "percentage": round(count / max(total_uses, 1) * 100, 1),
            })

        return ranking

    def compute_skill_usage(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """计算技能使用统计。

        Args:
            sessions: 会话列表。

        Returns:
            技能使用列表。
        """
        skill_counter: Counter = Counter()

        for s in sessions:
            skills = s.get("skills_used", [])
            if isinstance(skills, str):
                try:
                    skills = json.loads(skills)
                except (json.JSONDecodeError, TypeError):
                    skills = []

            for skill in skills:
                if isinstance(skill, str):
                    skill_counter[skill] += 1
                elif isinstance(skill, dict):
                    name = skill.get("name", skill.get("skill", "unknown"))
                    skill_counter[name] += 1

        total_uses = sum(skill_counter.values())
        usage = []
        for rank, (skill, count) in enumerate(skill_counter.most_common(), 1):
            usage.append({
                "rank": rank,
                "skill": skill,
                "count": count,
                "percentage": round(count / max(total_uses, 1) * 100, 1),
            })

        return usage

    def compute_activity_trend(self, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """计算每日活动趋势。

        Args:
            sessions: 会话列表。

        Returns:
            每日活动列表。
        """
        daily: dict[str, dict[str, int]] = defaultdict(
            lambda: {"sessions": 0, "messages": 0, "tokens": 0}
        )

        for s in sessions:
            timestamp = s.get("created_at", s.get("timestamp", ""))
            if not timestamp:
                continue

            # 解析日期
            try:
                if isinstance(timestamp, (int, float)):
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                else:
                    ts = timestamp.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(ts)
                date_str = dt.strftime("%Y-%m-%d")
            except (ValueError, OSError):
                continue

            input_tokens = s.get("input_tokens", 0)
            output_tokens = s.get("output_tokens", 0)
            cache_read = s.get("cache_read_tokens", 0)
            cache_write = s.get("cache_write_tokens", 0)

            daily[date_str]["sessions"] += 1
            daily[date_str]["messages"] += s.get("message_count", 0)
            daily[date_str]["tokens"] += input_tokens + output_tokens + cache_read + cache_write

        trend = []
        for date in sorted(daily.keys()):
            data = daily[date]
            trend.append({
                "date": date,
                "sessions": data["sessions"],
                "messages": data["messages"],
                "tokens": data["tokens"],
            })

        return trend

    def compute_top_sessions(
        self,
        sessions: list[dict[str, Any]],
        top_n: int = 5,
        sort_by: str = "tokens",
    ) -> list[dict[str, Any]]:
        """计算顶部会话。

        Args:
            sessions: 会话列表。
            top_n: 返回数量。
            sort_by: 排序字段（tokens, cost, messages）。

        Returns:
            顶部会话列表。
        """
        enriched = []
        for s in sessions:
            input_tokens = s.get("input_tokens", 0)
            output_tokens = s.get("output_tokens", 0)
            cache_read = s.get("cache_read_tokens", 0)
            cache_write = s.get("cache_write_tokens", 0)
            total_tokens = input_tokens + output_tokens + cache_read + cache_write
            cost = estimate_cost(
                s.get("model", ""),
                input_tokens, output_tokens, cache_read, cache_write,
            )

            enriched.append({
                "session_id": s.get("session_id", s.get("id", "unknown")),
                "title": s.get("title", s.get("name", "")),
                "model": s.get("model", "unknown"),
                "tokens": total_tokens,
                "cost": round(cost, 4),
                "messages": s.get("message_count", 0),
                "created_at": s.get("created_at", s.get("timestamp", "")),
            })

        # 排序
        sort_key = {
            "tokens": "tokens",
            "cost": "cost",
            "messages": "messages",
        }.get(sort_by, "tokens")

        enriched.sort(key=lambda x: x[sort_key], reverse=True)
        return enriched[:top_n]

    # ── 格式化 ──

    def format_terminal(self, report: InsightsReport | None = None, width: int = 80) -> str:
        """格式化为终端输出。

        Args:
            report: 报告实例。如果为 None 则生成新报告。
            width: 终端宽度。

        Returns:
            格式化的终端字符串。
        """
        if report is None:
            report = self.generate_report()
        return format_terminal(report, width)

    def format_bar_chart(self, data: list[dict[str, Any]], key: str = "count", max_width: int = 40) -> str:
        """格式化条形图。

        Args:
            data: 数据列表，每项包含 label/name 和 key 字段。
            key: 用于条形长度的字段名。
            max_width: 最大条形宽度。

        Returns:
            格式化的条形图字符串。
        """
        return format_bar_chart(data, key, max_width)

    # ── 内部方法 ──

    def _get_all_sessions(self) -> list[dict[str, Any]]:
        """获取所有会话。

        Returns:
            会话列表。
        """
        if self._db and hasattr(self._db, "conn") and self._db.conn:
            try:
                cursor = self._db.conn.execute("SELECT * FROM sessions ORDER BY created_at DESC")
                return [dict(row) for row in cursor.fetchall()]
            except Exception:
                return []
        return []

    def _compute_total_cost(self, sessions: list[dict[str, Any]]) -> float:
        """计算总成本。

        Args:
            sessions: 会话列表。

        Returns:
            总成本 (USD)。
        """
        total = 0.0
        for s in sessions:
            model = s.get("model", "")
            input_tokens = s.get("input_tokens", 0)
            output_tokens = s.get("output_tokens", 0)
            cache_read = s.get("cache_read_tokens", 0)
            cache_write = s.get("cache_write_tokens", 0)
            total += estimate_cost(model, input_tokens, output_tokens, cache_read, cache_write)
        return total

    def _compute_message_stats(self, sessions: list[dict[str, Any]]) -> dict[str, Any]:
        """计算消息统计。

        Args:
            sessions: 会话列表。

        Returns:
            消息统计数据。
        """
        message_counts = [s.get("message_count", 0) for s in sessions]
        total_messages = sum(message_counts)
        count = len(message_counts)

        if count == 0:
            return {
                "total_messages": 0,
                "avg_messages_per_session": 0,
                "max_messages": 0,
                "min_messages": 0,
                "median_messages": 0,
            }

        sorted_counts = sorted(message_counts)
        median = sorted_counts[count // 2] if count % 2 else (sorted_counts[count // 2 - 1] + sorted_counts[count // 2]) / 2

        return {
            "total_messages": total_messages,
            "avg_messages_per_session": round(total_messages / count, 1),
            "max_messages": max(message_counts),
            "min_messages": min(message_counts),
            "median_messages": median,
        }


# ─────────────────────────────────────────────
# 成本估算
# ─────────────────────────────────────────────
def estimate_cost(
    model: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> float:
    """估算模型调用的成本。

    Args:
        model: 模型名称。
        input_tokens: 输入 token 数。
        output_tokens: 输出 token 数。
        cache_read_tokens: 缓存读取 token 数。
        cache_write_tokens: 缓存写入 token 数。

    Returns:
        估算成本 (USD)。
    """
    if not model:
        model = "default"

    # 尝试匹配定价
    pricing = PRICING_DATABASE.get(model.lower())
    if pricing is None:
        # 尝试部分匹配
        for key, value in PRICING_DATABASE.items():
            if key in model.lower() or model.lower() in key:
                pricing = value
                break

    if pricing is None:
        pricing = PRICING_DATABASE["default"]

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0)
    cache_write_cost = (cache_write_tokens / 1_000_000) * pricing.get("cache_write", 0)

    return input_cost + output_cost + cache_read_cost + cache_write_cost


# ─────────────────────────────────────────────
# 格式化辅助函数
# ─────────────────────────────────────────────
def format_terminal(report: InsightsReport, width: int = 80) -> str:
    """格式化报告为终端输出。

    Args:
        report: 洞察报告。
        width: 终端宽度。

    Returns:
        格式化的终端字符串。
    """
    lines = []
    divider = "=" * width

    # 标题
    lines.append(divider)
    lines.append(" NanoHermes Insights Report".ljust(width))
    lines.append(divider)

    # 概览
    lines.append("")
    lines.append(" Overview")
    lines.append("─" * 40)
    lines.append(f"  Total Sessions:    {report.total_sessions}")
    lines.append(f"  Total Messages:    {report.total_messages}")
    lines.append(f"  Total Tokens:      {_format_number(report.total_tokens)}")
    lines.append(f"  Total Cost:        ${report.total_cost:.4f}")

    # 模型分解
    if report.model_breakdown:
        lines.append("")
        lines.append(" Model Breakdown")
        lines.append("─" * 40)
        for entry in report.model_breakdown:
            lines.append(
                f"  {entry['model']:<30} "
                f"{_format_number(entry['tokens']):>12} tokens  "
                f"${entry['cost']:.4f}"
            )

    # 工具排名
    if report.tool_ranking:
        lines.append("")
        lines.append(" Tool Ranking (Top 10)")
        lines.append("─" * 40)
        for entry in report.tool_ranking[:10]:
            bar = "█" * max(1, int(entry["percentage"] / 2))
            lines.append(
                f"  {entry['rank']:>2}. {entry['tool']:<20} "
                f"{entry['count']:>6}  {entry['percentage']:>5.1f}%  {bar}"
            )

    # 活动趋势
    if report.daily_activity:
        lines.append("")
        lines.append(" Daily Activity")
        lines.append("─" * 40)
        chart = format_bar_chart(
            report.daily_activity,
            key="sessions",
            max_width=width - 24,
        )
        lines.append(chart)

    # 顶部会话
    if report.top_sessions:
        lines.append("")
        lines.append(" Top Sessions")
        lines.append("─" * 40)
        for i, session in enumerate(report.top_sessions, 1):
            lines.append(
                f"  {i}. {session.get('title', session.get('session_id', 'N/A')):<40} "
                f"{_format_number(session['tokens']):>10} tokens"
            )

    lines.append("")
    lines.append(divider)
    return "\n".join(lines)


def format_bar_chart(
    data: list[dict[str, Any]],
    key: str = "count",
    max_width: int = 40,
) -> str:
    """格式化条形图。

    Args:
        data: 数据列表，每项包含 date/label 和 key 字段。
        key: 用于条形长度的字段名。
        max_width: 最大条形宽度。

    Returns:
        格式化的条形图字符串。
    """
    if not data:
        return "  (no data)"

    max_value = max(d.get(key, 0) for d in data)
    if max_value == 0:
        return "  (all zeros)"

    lines = []
    for entry in data:
        label = entry.get("date", entry.get("label", ""))
        value = entry.get(key, 0)
        bar_length = max(0, int((value / max_value) * max_width))
        bar = "█" * bar_length
        lines.append(f"  {label}  {bar:>{max_width}}  {value}")

    return "\n".join(lines)


def _format_number(n: int) -> str:
    """格式化数字，添加千位分隔符和缩写。

    Args:
        n: 数字。

    Returns:
        格式化字符串。
    """
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
