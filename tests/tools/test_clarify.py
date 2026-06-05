"""Tests for clarify tool."""

import json

import pytest


@pytest.fixture(autouse=True)
def _setup_clarify():
    """Setup clarify tool before each test."""
    from src.tools.clarify_tool import clear_pending_clarification
    clear_pending_clarification()
    yield
    clear_pending_clarification()


class TestClarifyTool:
    """Tests for clarify tool."""

    def test_clarify_basic_question(self):
        """Test clarify with basic question."""
        from src.tools.clarify_tool import clarify, get_pending_clarification

        result = clarify(question="What do you mean?")
        data = json.loads(result)

        assert data["status"] == "clarification_requested"
        assert data["question"] == "What do you mean?"
        assert data["allow_custom"] is True

        pending = get_pending_clarification()
        assert pending is not None
        assert pending["question"] == "What do you mean?"

    def test_clarify_with_options(self):
        """Test clarify with preset options."""
        from src.tools.clarify_tool import clarify, get_pending_clarification

        result = clarify(
            question="Which option?",
            options=["Option A", "Option B", "Option C"],
        )
        data = json.loads(result)

        assert len(data["options"]) == 3
        assert data["options"][0] == "Option A"

        pending = get_pending_clarification()
        assert len(pending["options"]) == 3

    def test_clarify_limits_options_to_4(self):
        """Test clarify limits options to 4."""
        from src.tools.clarify_tool import clarify

        result = clarify(
            question="Which option?",
            options=["A", "B", "C", "D", "E", "F"],
        )
        data = json.loads(result)

        assert len(data["options"]) == 4

    def test_clarify_disable_custom(self):
        """Test clarify with custom input disabled."""
        from src.tools.clarify_tool import clarify

        result = clarify(
            question="Choose one:",
            options=["Yes", "No"],
            allow_custom=False,
        )
        data = json.loads(result)

        assert data["allow_custom"] is False

    def test_respond_to_clarification(self):
        """Test responding to clarification."""
        from src.tools.clarify_tool import clarify, respond_to_clarification, get_pending_clarification

        clarify(question="What?", options=["A", "B"])
        result = respond_to_clarification("A")
        data = json.loads(result)

        assert data["status"] == "success"
        assert data["response"] == "A"

        pending = get_pending_clarification()
        assert pending["status"] == "answered"
        assert pending["response"] == "A"

    def test_respond_without_pending(self):
        """Test responding without pending clarification."""
        from src.tools.clarify_tool import respond_to_clarification

        result = respond_to_clarification("test")
        data = json.loads(result)

        assert "error" in data

    def test_clear_pending(self):
        """Test clearing pending clarification."""
        from src.tools.clarify_tool import clarify, clear_pending_clarification, get_pending_clarification

        clarify(question="What?")
        clear_pending_clarification()

        assert get_pending_clarification() is None


class TestClarifyIntegration:
    """Integration tests for clarify tool."""

    def test_clarify_via_dispatcher(self):
        """Test clarify tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import clarify_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(clarify_tools)

        result = dispatch("clarify", {
            "question": "Which one?",
            "options": ["First", "Second"],
        })
        data = json.loads(result)

        assert data["status"] == "clarification_requested"
        assert data["question"] == "Which one?"
        assert len(data["options"]) == 2

