"""Tests for insights engine module."""

import pytest
from unittest.mock import MagicMock, patch

from src.insights.engine import (
    InsightsEngine,
    InsightsReport,
    PRICING_DATABASE,
    estimate_cost,
    format_terminal,
    format_bar_chart,
    _format_number,
)


class TestInsightsReport:
    """Tests for InsightsReport dataclass."""

    def test_default_values(self):
        """Test default values."""
        report = InsightsReport()
        assert report.total_sessions == 0
        assert report.total_messages == 0
        assert report.total_tokens == 0
        assert report.total_cost == 0.0
        assert report.model_breakdown == []
        assert report.tool_ranking == []
        assert report.daily_activity == []
        assert report.top_sessions == []
        assert report.message_stats == {}

    def test_custom_values(self):
        """Test custom values."""
        report = InsightsReport(
            total_sessions=10,
            total_messages=100,
            total_tokens=50000,
            total_cost=5.50,
            model_breakdown=[{"model": "gpt-4o", "tokens": 30000}],
            tool_ranking=[{"tool": "terminal", "count": 50}],
            daily_activity=[{"date": "2024-01-01", "sessions": 5}],
            top_sessions=[{"id": "abc123", "tokens": 10000}],
        )
        assert report.total_sessions == 10
        assert report.total_messages == 100
        assert report.total_tokens == 50000
        assert report.total_cost == 5.50
        assert len(report.model_breakdown) == 1
        assert len(report.tool_ranking) == 1

    def test_format_terminal(self):
        """Test format_terminal method."""
        report = InsightsReport(
            total_sessions=5,
            total_messages=50,
            total_tokens=100000,
            total_cost=1.5,
        )
        output = report.format_terminal(width=80)
        assert "NanoHermes Insights Report" in output
        assert "5" in output
        assert "50" in output


class TestInsightsEngine:
    """Tests for InsightsEngine class."""

    def test_init_with_db(self):
        """Test initialization with session database."""
        mock_db = MagicMock()
        engine = InsightsEngine(mock_db)
        assert engine._db == mock_db

    def test_init_without_db(self):
        """Test initialization without session database."""
        engine = InsightsEngine(None)
        assert engine._db is None

    def test_generate_report_no_db(self):
        """Test generate_report returns empty report when no db."""
        engine = InsightsEngine(None)
        report = engine.generate_report()
        assert isinstance(report, InsightsReport)
        assert report.total_sessions == 0
        assert report.total_tokens == 0

    def test_generate_report_with_db(self):
        """Test generate_report queries database."""
        mock_db = MagicMock()
        mock_db.conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "abc123",
                "model": "gpt-4o",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 200,
                "cache_write_tokens": 100,
                "message_count": 10,
                "tool_calls": [],
                "skills_used": [],
                "created_at": "2024-01-01T00:00:00Z",
            },
            {
                "session_id": "def456",
                "model": "claude-sonnet-4-20250514",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cache_read_tokens": 400,
                "cache_write_tokens": 200,
                "message_count": 20,
                "tool_calls": [],
                "skills_used": [],
                "created_at": "2024-01-02T00:00:00Z",
            },
        ]
        mock_db.conn.execute.return_value = mock_cursor

        engine = InsightsEngine(mock_db)
        report = engine.generate_report()

        assert report.total_sessions == 2
        assert report.total_messages == 30

    def test_generate_report_empty_db(self):
        """Test generate_report handles empty database."""
        mock_db = MagicMock()
        mock_db.conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_db.conn.execute.return_value = mock_cursor

        engine = InsightsEngine(mock_db)
        report = engine.generate_report()

        assert report.total_sessions == 0
        assert report.total_tokens == 0

    def test_generate_report_db_no_conn(self):
        """Test generate_report handles database without connection."""
        mock_db = MagicMock()
        mock_db.conn = None

        engine = InsightsEngine(mock_db)
        report = engine.generate_report()

        assert report.total_sessions == 0

    def test_get_all_sessions_no_db(self):
        """Test _get_all_sessions returns empty when no db."""
        engine = InsightsEngine(None)
        sessions = engine._get_all_sessions()
        assert sessions == []

    def test_get_all_sessions_with_db(self):
        """Test _get_all_sessions queries database."""
        mock_db = MagicMock()
        mock_db.conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"session_id": "abc123", "title": "Test Session"},
        ]
        mock_db.conn.execute.return_value = mock_cursor

        engine = InsightsEngine(mock_db)
        sessions = engine._get_all_sessions()

        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "abc123"

    def test_get_all_sessions_db_no_conn(self):
        """Test _get_all_sessions handles database without connection."""
        mock_db = MagicMock()
        mock_db.conn = None

        engine = InsightsEngine(mock_db)
        sessions = engine._get_all_sessions()

        assert sessions == []

    def test_get_all_sessions_db_exception(self):
        """Test _get_all_sessions handles database exceptions."""
        mock_db = MagicMock()
        mock_db.conn = MagicMock()
        mock_db.conn.execute.side_effect = Exception("DB error")

        engine = InsightsEngine(mock_db)
        sessions = engine._get_all_sessions()

        assert sessions == []

    def test_get_sessions_with_source_filter(self):
        """Test get_sessions filters by source."""
        engine = InsightsEngine(None)
        # Manually test with mocked sessions
        with patch.object(engine, '_get_all_sessions') as mock_get:
            mock_get.return_value = [
                {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50},
                {"model": "claude-sonnet-4-20250514", "input_tokens": 200, "output_tokens": 100},
            ]
            sessions = engine.get_sessions(source="gpt")
            assert len(sessions) == 1
            assert sessions[0]["model"] == "gpt-4o"

    def test_get_sessions_with_limit(self):
        """Test get_sessions respects limit."""
        engine = InsightsEngine(None)
        with patch.object(engine, '_get_all_sessions') as mock_get:
            mock_get.return_value = [
                {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50},
                {"model": "gpt-4o-mini", "input_tokens": 200, "output_tokens": 100},
                {"model": "claude-sonnet-4-20250514", "input_tokens": 300, "output_tokens": 150},
            ]
            sessions = engine.get_sessions(limit=2)
            assert len(sessions) == 2


class TestComputeMethods:
    """Tests for compute methods."""

    def _make_sessions(self):
        """Create test sessions."""
        return [
            {
                "session_id": "s1",
                "model": "gpt-4o",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 200,
                "cache_write_tokens": 100,
                "message_count": 10,
                "tool_calls": [
                    {"name": "terminal"},
                    {"name": "read_file"},
                    {"name": "terminal"},
                ],
                "skills_used": ["python-dev", "web-search"],
                "created_at": "2024-01-01T10:00:00Z",
                "title": "Test Session 1",
            },
            {
                "session_id": "s2",
                "model": "claude-sonnet-4-20250514",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cache_read_tokens": 400,
                "cache_write_tokens": 200,
                "message_count": 20,
                "tool_calls": [
                    {"name": "write_file"},
                    {"name": "terminal"},
                ],
                "skills_used": ["python-dev"],
                "created_at": "2024-01-02T10:00:00Z",
                "title": "Test Session 2",
            },
        ]

    def test_compute_overview(self):
        """Test compute_overview method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        overview = engine.compute_overview(sessions)

        assert overview["total_sessions"] == 2
        assert overview["total_messages"] == 30
        assert overview["total_tokens"] > 0
        assert overview["total_cost"] >= 0
        assert "avg_tokens_per_session" in overview
        assert "avg_cost_per_session" in overview

    def test_compute_model_breakdown(self):
        """Test compute_model_breakdown method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        breakdown = engine.compute_model_breakdown(sessions)

        assert len(breakdown) == 2
        models = [b["model"] for b in breakdown]
        assert "gpt-4o" in models
        assert "claude-sonnet-4-20250514" in models

        # Check ordering (by tokens desc)
        assert breakdown[0]["tokens"] >= breakdown[1]["tokens"]

    def test_compute_platform_breakdown(self):
        """Test compute_platform_breakdown method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        breakdown = engine.compute_platform_breakdown(sessions)

        assert len(breakdown) >= 2
        platforms = [b["platform"] for b in breakdown]
        assert "OpenAI" in platforms
        assert "Anthropic" in platforms

    def test_compute_tool_ranking(self):
        """Test compute_tool_ranking method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        ranking = engine.compute_tool_ranking(sessions)

        assert len(ranking) > 0
        assert ranking[0]["rank"] == 1
        assert "terminal" in [r["tool"] for r in ranking]
        # terminal appears 3 times (most)
        terminal_entry = next(r for r in ranking if r["tool"] == "terminal")
        assert terminal_entry["count"] == 3

    def test_compute_tool_ranking_string_tool_calls(self):
        """Test compute_tool_ranking with string tool_calls."""
        engine = InsightsEngine(None)
        sessions = [
            {
                "session_id": "s1",
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50,
                "message_count": 5,
                "tool_calls": '[{"name": "terminal"}, {"name": "read_file"}]',
                "skills_used": [],
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]
        ranking = engine.compute_tool_ranking(sessions)
        assert len(ranking) == 2

    def test_compute_tool_ranking_empty(self):
        """Test compute_tool_ranking with empty sessions."""
        engine = InsightsEngine(None)
        ranking = engine.compute_tool_ranking([])
        assert ranking == []

    def test_compute_skill_usage(self):
        """Test compute_skill_usage method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        usage = engine.compute_skill_usage(sessions)

        assert len(usage) > 0
        python_entry = next((u for u in usage if u["skill"] == "python-dev"), None)
        assert python_entry is not None
        assert python_entry["count"] == 2  # appears in both sessions

    def test_compute_skill_usage_string_skills(self):
        """Test compute_skill_usage with string skills_used."""
        engine = InsightsEngine(None)
        sessions = [
            {
                "session_id": "s1",
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50,
                "message_count": 5,
                "tool_calls": [],
                "skills_used": '["python-dev", "web-search"]',
                "created_at": "2024-01-01T00:00:00Z",
            },
        ]
        usage = engine.compute_skill_usage(sessions)
        assert len(usage) == 2

    def test_compute_activity_trend(self):
        """Test compute_activity_trend method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        trend = engine.compute_activity_trend(sessions)

        assert len(trend) == 2
        assert trend[0]["date"] == "2024-01-01"
        assert trend[1]["date"] == "2024-01-02"
        assert trend[0]["sessions"] == 1
        assert trend[1]["sessions"] == 1

    def test_compute_activity_trend_empty(self):
        """Test compute_activity_trend with empty sessions."""
        engine = InsightsEngine(None)
        trend = engine.compute_activity_trend([])
        assert trend == []

    def test_compute_activity_trend_timestamp(self):
        """Test compute_activity_trend with unix timestamps."""
        engine = InsightsEngine(None)
        sessions = [
            {
                "session_id": "s1",
                "model": "gpt-4o",
                "input_tokens": 100,
                "output_tokens": 50,
                "message_count": 5,
                "tool_calls": [],
                "skills_used": [],
                "created_at": 1704067200,  # 2024-01-01
            },
        ]
        trend = engine.compute_activity_trend(sessions)
        assert len(trend) == 1

    def test_compute_top_sessions(self):
        """Test compute_top_sessions method."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        top = engine.compute_top_sessions(sessions, top_n=1)

        assert len(top) == 1
        assert "session_id" in top[0]
        assert "tokens" in top[0]
        assert "cost" in top[0]

    def test_compute_top_sessions_sort_by_cost(self):
        """Test compute_top_sessions sorted by cost."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        top = engine.compute_top_sessions(sessions, top_n=2, sort_by="cost")

        assert len(top) == 2
        assert top[0]["cost"] >= top[1]["cost"]

    def test_compute_top_sessions_sort_by_messages(self):
        """Test compute_top_sessions sorted by messages."""
        engine = InsightsEngine(None)
        sessions = self._make_sessions()
        top = engine.compute_top_sessions(sessions, top_n=2, sort_by="messages")

        assert len(top) == 2
        assert top[0]["messages"] >= top[1]["messages"]


class TestCostEstimation:
    """Tests for cost estimation."""

    def test_estimate_cost_gpt4o(self):
        """Test cost estimation for GPT-4o."""
        cost = estimate_cost("gpt-4o", input_tokens=1_000_000, output_tokens=500_000)
        # input: 1M * $2.5/M = $2.5, output: 0.5M * $10/M = $5.0
        assert abs(cost - 7.5) < 0.01

    def test_estimate_cost_claude_sonnet(self):
        """Test cost estimation for Claude Sonnet."""
        cost = estimate_cost("claude-sonnet-4-20250514", input_tokens=1_000_000, output_tokens=500_000)
        # input: 1M * $3/M = $3.0, output: 0.5M * $15/M = $7.5
        assert abs(cost - 10.5) < 0.01

    def test_estimate_cost_with_cache(self):
        """Test cost estimation with cache tokens."""
        cost = estimate_cost(
            "gpt-4o",
            input_tokens=1_000_000,
            output_tokens=500_000,
            cache_read_tokens=200_000,
            cache_write_tokens=100_000,
        )
        # input: $2.5, output: $5.0, cache_read: 0.2M*$1.25/M=$0.25, cache_write: 0.1M*$2.5/M=$0.25
        assert abs(cost - 8.0) < 0.01

    def test_estimate_cost_unknown_model(self):
        """Test cost estimation for unknown model uses default."""
        cost_unknown = estimate_cost("unknown-model-xyz", input_tokens=1_000_000)
        cost_default = estimate_cost("default", input_tokens=1_000_000)
        assert abs(cost_unknown - cost_default) < 0.01

    def test_estimate_cost_empty_model(self):
        """Test cost estimation with empty model uses default."""
        cost = estimate_cost("", input_tokens=1_000_000)
        default_cost = estimate_cost("default", input_tokens=1_000_000)
        assert abs(cost - default_cost) < 0.01

    def test_estimate_cost_partial_match(self):
        """Test cost estimation with partial model name match."""
        cost = estimate_cost("gpt-4o-2024-08-06", input_tokens=1_000_000)
        assert cost > 0

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        cost = estimate_cost("gpt-4o")
        assert cost == 0.0

    def test_pricing_database_has_defaults(self):
        """Test pricing database has default entry."""
        assert "default" in PRICING_DATABASE
        assert "input" in PRICING_DATABASE["default"]
        assert "output" in PRICING_DATABASE["default"]

    def test_pricing_database_multiple_providers(self):
        """Test pricing database covers multiple providers."""
        models = list(PRICING_DATABASE.keys())
        has_anthropic = any("claude" in m for m in models)
        has_openai = any("gpt" in m or "o1" in m or "o3" in m for m in models)
        assert has_anthropic
        assert has_openai


class TestFormatting:
    """Tests for formatting functions."""

    def test_format_terminal_basic(self):
        """Test format_terminal with basic report."""
        report = InsightsReport(
            total_sessions=5,
            total_messages=50,
            total_tokens=100000,
            total_cost=1.5,
        )
        output = format_terminal(report, width=80)

        assert "NanoHermes Insights Report" in output
        assert "Overview" in output
        assert "5" in output

    def test_format_terminal_with_model_breakdown(self):
        """Test format_terminal with model breakdown."""
        report = InsightsReport(
            total_sessions=2,
            total_tokens=5000,
            total_cost=0.5,
            model_breakdown=[
                {"model": "gpt-4o", "tokens": 3000, "cost": 0.3},
                {"model": "claude-sonnet", "tokens": 2000, "cost": 0.2},
            ],
        )
        output = format_terminal(report)
        assert "Model Breakdown" in output
        assert "gpt-4o" in output

    def test_format_terminal_with_tool_ranking(self):
        """Test format_terminal with tool ranking."""
        report = InsightsReport(
            total_sessions=1,
            total_tokens=1000,
            tool_ranking=[
                {"rank": 1, "tool": "terminal", "count": 10, "percentage": 50.0},
                {"rank": 2, "tool": "read_file", "count": 5, "percentage": 25.0},
            ],
        )
        output = format_terminal(report)
        assert "Tool Ranking" in output
        assert "terminal" in output

    def test_format_bar_chart_basic(self):
        """Test format_bar_chart with basic data."""
        data = [
            {"date": "2024-01-01", "sessions": 5},
            {"date": "2024-01-02", "sessions": 10},
            {"date": "2024-01-03", "sessions": 3},
        ]
        output = format_bar_chart(data, key="sessions", max_width=20)
        assert "2024-01-01" in output
        assert "2024-01-02" in output

    def test_format_bar_chart_empty(self):
        """Test format_bar_chart with empty data."""
        output = format_bar_chart([])
        assert "no data" in output

    def test_format_bar_chart_all_zeros(self):
        """Test format_bar_chart with all zeros."""
        data = [
            {"date": "2024-01-01", "sessions": 0},
            {"date": "2024-01-02", "sessions": 0},
        ]
        output = format_bar_chart(data, key="sessions")
        assert "all zeros" in output

    def test_format_bar_chart_peak_normalization(self):
        """Test format_bar_chart peak normalization."""
        data = [
            {"date": "d1", "count": 100},
            {"date": "d2", "count": 50},
        ]
        output = format_bar_chart(data, key="count", max_width=10)
        # d1 should have 10 chars, d2 should have 5
        lines = output.split("\n")
        d1_bar = lines[0].count("█")
        d2_bar = lines[1].count("█")
        assert d1_bar == 10
        assert d2_bar == 5

    def test_format_number(self):
        """Test _format_number helper."""
        assert _format_number(500) == "500"
        assert _format_number(1500) == "1.5K"
        assert _format_number(1500000) == "1.5M"

    def test_format_terminal_divider(self):
        """Test format_terminal includes dividers."""
        report = InsightsReport(total_sessions=1)
        output = format_terminal(report, width=60)
        assert "=" * 60 in output


class TestMessageStats:
    """Tests for message statistics."""

    def test_get_message_stats(self):
        """Test get_message_stats method."""
        engine = InsightsEngine(None)
        sessions = [
            {"session_id": "s1", "message_count": 10},
            {"session_id": "s2", "message_count": 20},
            {"session_id": "s3", "message_count": 5},
        ]
        stats = engine.get_message_stats(sessions)

        assert stats["total_messages"] == 35
        assert stats["avg_messages_per_session"] > 0
        assert stats["max_messages"] == 20
        assert stats["min_messages"] == 5

    def test_get_message_stats_empty(self):
        """Test get_message_stats with empty sessions."""
        engine = InsightsEngine(None)
        stats = engine.get_message_stats([])

        assert stats["total_messages"] == 0
        assert stats["avg_messages_per_session"] == 0

    def test_compute_message_stats_median(self):
        """Test message stats median calculation."""
        engine = InsightsEngine(None)
        sessions = [
            {"session_id": f"s{i}", "message_count": i * 10}
            for i in range(1, 6)  # 10, 20, 30, 40, 50
        ]
        stats = engine._compute_message_stats(sessions)
        assert stats["median_messages"] == 30

    def test_compute_message_stats_even_count(self):
        """Test message stats with even number of sessions."""
        engine = InsightsEngine(None)
        sessions = [
            {"session_id": "s1", "message_count": 10},
            {"session_id": "s2", "message_count": 20},
        ]
        stats = engine._compute_message_stats(sessions)
        assert stats["median_messages"] == 15.0
