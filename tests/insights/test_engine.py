"""Tests for insights engine module."""

import pytest
from unittest.mock import MagicMock, patch

from src.insights.engine import InsightsEngine, InsightsReport


class TestInsightsReport:
    """Tests for InsightsReport dataclass."""

    def test_default_values(self):
        """Test default values."""
        report = InsightsReport()
        assert report.total_sessions == 0
        assert report.total_messages == 0
        assert report.total_tokens == 0
        assert report.total_cost == 0.0
        assert report.model_breakdown is None
        assert report.tool_ranking is None
        assert report.daily_activity is None
        assert report.top_sessions is None

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

    def test_generate_report_with_db(self):
        """Test generate_report queries database."""
        mock_db = MagicMock()
        mock_db.conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "session_id": "abc123",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_read_tokens": 200,
                "cache_write_tokens": 100,
            },
            {
                "session_id": "def456",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cache_read_tokens": 400,
                "cache_write_tokens": 200,
            },
        ]
        mock_db.conn.execute.return_value = mock_cursor

        engine = InsightsEngine(mock_db)
        report = engine.generate_report()

        assert report.total_sessions == 2
        # Total tokens = (1000+500) + (2000+1000) = 4500
        assert report.total_tokens == 4500

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
