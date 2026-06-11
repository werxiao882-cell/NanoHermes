"""Tests for clarify tools module."""

import pytest
import json
from unittest.mock import patch

from src.tools.impls.clarify_tool import (
    clarify,
    get_pending_clarification,
    respond_to_clarification,
    clear_pending_clarification,
)


@pytest.fixture(autouse=True)
def _clear_pending():
    """Clear pending clarification before and after each test."""
    clear_pending_clarification()
    yield
    clear_pending_clarification()


class TestClarifyTool:
    """Tests for clarify tool function."""

    def test_clarify_basic_question(self):
        """Test clarify with basic question."""
        result = json.loads(clarify(question="What do you mean?"))
        assert result["status"] == "clarification_requested"
        assert result["question"] == "What do you mean?"
        assert result["allow_custom"] is True

    def test_clarify_with_options(self):
        """Test clarify with preset choices."""
        result = json.loads(clarify(
            question="Which option?",
            choices=["Option A", "Option B", "Option C"],
        ))
        assert len(result["choices"]) == 3
        assert result["choices"][0] == "Option A"

    def test_clarify_limits_options_to_4(self):
        """Test clarify limits choices to 4."""
        result = json.loads(clarify(
            question="Which option?",
            choices=["A", "B", "C", "D", "E", "F"],
        ))
        assert len(result["choices"]) == 4

    def test_clarify_disable_custom(self):
        """Test clarify with custom input disabled."""
        result = json.loads(clarify(
            question="Choose one:",
            choices=["Yes", "No"],
            allow_custom=False,
        ))
        assert result["allow_custom"] is False


class TestPendingClarification:
    """Tests for pending clarification management."""

    def test_get_pending_after_clarify(self):
        """Test get_pending returns clarification after clarify call."""
        clarify(question="Test?")
        pending = get_pending_clarification()
        assert pending is not None
        assert pending["question"] == "Test?"
        assert pending["status"] == "pending"

    def test_get_pending_none(self):
        """Test get_pending returns None when no pending clarification."""
        assert get_pending_clarification() is None

    def test_respond_to_clarification(self):
        """Test responding to clarification."""
        clarify(question="Test?")
        result = json.loads(respond_to_clarification("Answer"))
        assert result["status"] == "success"
        assert result["response"] == "Answer"

    def test_respond_updates_pending(self):
        """Test respond updates pending clarification status."""
        clarify(question="Test?")
        respond_to_clarification("Answer")
        pending = get_pending_clarification()
        assert pending["status"] == "answered"
        assert pending["response"] == "Answer"

    def test_respond_without_pending(self):
        """Test responding without pending clarification."""
        result = json.loads(respond_to_clarification("Answer"))
        assert "error" in result

    def test_clear_pending(self):
        """Test clearing pending clarification."""
        clarify(question="Test?")
        clear_pending_clarification()
        assert get_pending_clarification() is None


class TestClarifyIntegration:
    """Integration tests for clarify tool via dispatcher."""

    def test_clarify_via_dispatcher(self):
        """Test clarify tool via dispatcher."""
        from src.tools.core.registry import ToolRegistry
        from src.tools.impls import clarify_tool
        import importlib
        from src.tools.core.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(clarify_tool)

        result = dispatch("clarify", {"question": "What do you mean?"})
        data = json.loads(result)
        assert data["status"] == "clarification_requested"
        assert data["question"] == "What do you mean?"


