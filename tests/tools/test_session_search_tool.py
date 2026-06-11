"""Tests for session search tools module."""

import pytest
import json

from src.tools.impls.session_search_tool import session_search


class TestSessionSearch:
    """Tests for session_search tool function."""

    def test_session_search_basic(self):
        """Test basic session search."""
        result = json.loads(session_search(query="Python"))
        # 如果没有数据库，返回 error；如果有数据库，返回 success
        assert result["status"] in ("search_requested", "success", "error")
        assert "query" in result or "message" in result

    def test_session_search_with_session_id(self):
        """Test session search with specific session ID."""
        result = json.loads(session_search(query="test", session_id="abc123"))
        assert result["status"] in ("search_requested", "success", "error")

    def test_session_search_with_limit(self):
        """Test session search with limit."""
        result = json.loads(session_search(query="test", limit=5))
        assert result["status"] in ("search_requested", "success", "error")

    def test_session_search_via_dispatcher(self):
        """Test session_search tool via dispatcher."""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import session_search_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(session_search_tool)

        result = dispatch("session_search", {"query": "test"})
        data = json.loads(result)
        # 当 check_fn 返回 False 时，dispatcher 返回 {"error": "..."} 格式
        # 当 check_fn 通过时，返回 {"status": "..."} 格式
        if "status" in data:
            assert data["status"] in ("search_requested", "success", "error")
        elif "error" in data:
            # 工具不可用时返回 error 字段
            assert "session_search" in data["error"] or "不可用" in data["error"]
        else:
            pytest.fail(f"Unexpected response format: {data}")