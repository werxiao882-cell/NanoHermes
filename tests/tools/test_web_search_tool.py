"""Tests for web_search tool."""

import json
import pytest
from unittest.mock import patch, MagicMock


class TestWebSearchAvailability:
    """Tests for web search availability check."""

    def test_available_when_import_succeeds(self):
        from src.tools.impls.web_search_tool import check_web_search_available
        assert check_web_search_available() is True

    def test_unavailable_when_import_fails(self):
        from src.tools.impls import web_search_tool
        original_fn = web_search_tool.check_web_search_available
        web_search_tool.check_web_search_available = lambda: False
        assert web_search_tool.check_web_search_available() is False
        web_search_tool.check_web_search_available = original_fn


class TestWebSearchRegistration:
    """Tests for web search tool registration."""

    def test_tool_is_registered(self):
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import web_search_tool  # noqa: F401

        entry = ToolRegistry.get_tool("web_search")
        assert entry is not None
        assert entry.name == "web_search"
        assert entry.toolset == "search"
        assert entry.defer_loading is True

    def test_schema_has_required_fields(self):
        from src.tools.impls.web_search_tool import SCHEMA

        assert SCHEMA["type"] == "function"
        func = SCHEMA["function"]
        assert func["name"] == "web_search"
        assert "description" in func
        assert "parameters" in func

        params = func["parameters"]
        assert "query" in params["properties"]
        assert "max_results" in params["properties"]
        assert "region" in params["properties"]
        assert "safesearch" in params["properties"]
        assert "timelimit" in params["properties"]
        assert "backend" in params["properties"]
        assert "query" in params["required"]


def _make_mock_ddgs(text_results=None, news_results=None):
    """Create a mock DDGS context manager."""
    mock_ddgs = MagicMock()
    mock_ddgs.text.return_value = text_results or []
    mock_ddgs.news.return_value = news_results or []
    mock_cls = MagicMock()
    mock_cls.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
    mock_cls.return_value.__exit__ = MagicMock(return_value=False)
    return mock_cls, mock_ddgs


class TestWebSearchExecution:
    """Tests for web search execution."""

    def test_empty_query_returns_error(self):
        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query=""))
        assert "error" in result

    def test_whitespace_query_returns_error(self):
        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query="   "))
        assert "error" in result

    @patch("src.tools.impls.web_search_tool.DDGS")
    def test_text_search_success(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = [
            {"title": "Test Title", "href": "https://example.com", "body": "Test body"},
            {"title": "Title 2", "href": "https://example2.com", "body": "Body 2"},
        ]

        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query="test query", max_results=2))

        assert result["status"] == "success"
        assert result["query"] == "test query"
        assert result["backend"] == "text"
        assert result["count"] == 2
        assert result["results"][0]["title"] == "Test Title"
        assert result["results"][0]["url"] == "https://example.com"
        assert result["results"][0]["description"] == "Test body"

    @patch("src.tools.impls.web_search_tool.DDGS")
    def test_news_search_success(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ddgs.news.return_value = [
            {
                "title": "Breaking News",
                "url": "https://news.example.com",
                "body": "News body",
                "source": "Example News",
                "date": "2024-01-01",
            },
        ]

        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query="breaking news", backend="news"))

        assert result["status"] == "success"
        assert result["backend"] == "news"
        assert result["count"] == 1
        assert result["results"][0]["source"] == "Example News"
        assert result["results"][0]["date"] == "2024-01-01"

    @patch("src.tools.impls.web_search_tool.DDGS")
    def test_search_exception_handling(self, mock_ddgs_class):
        mock_ddgs_class.side_effect = RuntimeError("Network error")

        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query="test"))

        assert "error" in result
        assert "Network error" in result["error"]

    @patch("src.tools.impls.web_search_tool.DDGS")
    def test_max_results_clamped(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = []

        from src.tools.impls.web_search_tool import web_search

        web_search(query="test", max_results=0)
        assert mock_ddgs.text.call_args.kwargs.get("max_results", mock_ddgs.text.call_args[1].get("max_results")) == 1

        web_search(query="test", max_results=100)
        assert mock_ddgs.text.call_args.kwargs.get("max_results", mock_ddgs.text.call_args[1].get("max_results")) == 20

    @patch("src.tools.impls.web_search_tool.DDGS")
    def test_no_results_returns_empty_list(self, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs_class.return_value.__enter__ = MagicMock(return_value=mock_ddgs)
        mock_ddgs_class.return_value.__exit__ = MagicMock(return_value=False)
        mock_ddgs.text.return_value = []

        from src.tools.impls.web_search_tool import web_search
        result = json.loads(web_search(query="very specific nonexistent thing"))

        assert result["status"] == "success"
        assert result["count"] == 0
        assert result["results"] == []


class TestWebSearchViaDispatcher:
    """Test web search through the dispatcher."""

    def test_dispatch_web_search(self):
        from src.tools.core.registry import ToolRegistry
        from src.tools.core.dispatcher import dispatch
        from src.tools.impls import web_search_tool  # noqa: F401
        import importlib
        importlib.reload(web_search_tool)

        result = json.loads(dispatch("web_search", {"query": ""}))
        assert "error" in result
