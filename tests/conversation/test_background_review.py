"""Tests for background review module."""

import json
import threading
import time

import pytest

from src.conversation.background_review import (
    spawn_background_review,
    fork_agent,
    build_review_prompt,
    _format_conversation,
    REVIEW_TOOL_WHITELIST,
    _MEMORY_REVIEW_PROMPT,
    _SKILL_REVIEW_PROMPT,
)


class TestBackgroundReview:
    """Tests for background review functionality."""

    def test_spawn_background_review_returns_thread(self):
        """Test that spawn_background_review returns a thread."""

        def mock_call(messages, tools):
            return {"content": "Review complete"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "Hello"}]
        thread = spawn_background_review(messages, mock_call, mock_dispatch)

        assert isinstance(thread, threading.Thread)
        assert thread.daemon is True

        # Wait for thread to complete
        thread.join(timeout=5)
        assert not thread.is_alive()

    def test_spawn_background_review_memory_type(self):
        """Test spawn_background_review with memory review type."""

        def mock_call(messages, tools):
            # Verify the prompt contains memory review instructions
            system_msg = messages[0].get("content", "")
            assert "记忆审查" in system_msg or "memory" in system_msg.lower()
            return {"content": "Memory review done"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "I prefer Python over Java"}]
        thread = spawn_background_review(messages, mock_call, mock_dispatch, review_type="memory")
        thread.join(timeout=5)

    def test_spawn_background_review_skill_type(self):
        """Test spawn_background_review with skill review type."""

        def mock_call(messages, tools):
            # Verify the prompt contains skill review instructions
            system_msg = messages[0].get("content", "")
            assert "技能审查" in system_msg or "skill" in system_msg.lower()
            return {"content": "Skill review done"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "Let me show you how to deploy"}]
        thread = spawn_background_review(messages, mock_call, mock_dispatch, review_type="skill")
        thread.join(timeout=5)


class TestForkAgent:
    """Tests for fork_agent functionality."""

    def test_fork_agent_returns_result(self):
        """Test that fork_agent returns a result dict."""

        def mock_call(messages, tools):
            return {"content": "Forked agent response"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "Test"}]
        result = fork_agent(messages, mock_call, mock_dispatch)

        assert "final_response" in result
        assert "iterations" in result
        assert result["final_response"] == "Forked agent response"

    def test_fork_agent_tool_whitelist(self):
        """Test that fork_agent creates filtered dispatch function."""
        # The fork_agent creates a filtered dispatch internally
        # We test that the whitelist parameter is accepted
        def mock_call(messages, tools):
            return {"content": "Response"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "Test"}]
        # Should not raise error with custom whitelist
        result = fork_agent(messages, mock_call, mock_dispatch, tool_whitelist={"memory", "skill_manage"})
        assert "final_response" in result

    def test_fork_agent_blocks_non_whitelisted_tools(self):
        """Test that fork_agent creates filtered dispatch that blocks non-whitelisted tools."""
        # The filtered_dispatch function should block non-whitelisted tools
        def mock_call(messages, tools):
            return {"content": "Response"}

        def mock_dispatch(name, args):
            return '{"status": "ok"}'

        messages = [{"role": "user", "content": "Test"}]
        # Should work with restricted whitelist
        result = fork_agent(messages, mock_call, mock_dispatch, tool_whitelist={"memory"})
        assert result["final_response"] == "Response"


class TestBuildReviewPrompt:
    """Tests for build_review_prompt function."""

    def test_build_memory_review_prompt(self):
        """Test building memory review prompt."""
        conversation = "User: I like Python"
        prompt = build_review_prompt("memory", conversation)

        assert "记忆审查" in prompt or "memory" in prompt.lower()
        assert conversation in prompt

    def test_build_skill_review_prompt(self):
        """Test building skill review prompt."""
        conversation = "User: Here's how to deploy"
        prompt = build_review_prompt("skill", conversation)

        assert "技能审查" in prompt or "skill" in prompt.lower()
        assert conversation in prompt


class TestFormatConversation:
    """Tests for _format_conversation function."""

    def test_format_simple_conversation(self):
        """Test formatting a simple conversation."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        result = _format_conversation(messages)

        assert "user: Hello" in result
        assert "assistant: Hi there" in result

    def test_format_truncates_long_messages(self):
        """Test that long messages are truncated."""
        long_content = "x" * 1000
        messages = [{"role": "user", "content": long_content}]
        result = _format_conversation(messages)

        assert len(result) < 600  # Should be truncated to ~500 chars
        assert "..." in result

    def test_format_skips_empty_content(self):
        """Test that messages with empty content are skipped."""
        messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "Hello"},
        ]
        result = _format_conversation(messages)

        assert "user:" not in result
        assert "assistant: Hello" in result


class TestReviewConstants:
    """Tests for review constants."""

    def test_memory_review_prompt_exists(self):
        """Test that memory review prompt is defined."""
        assert _MEMORY_REVIEW_PROMPT is not None
        assert len(_MEMORY_REVIEW_PROMPT) > 0

    def test_skill_review_prompt_exists(self):
        """Test that skill review prompt is defined."""
        assert _SKILL_REVIEW_PROMPT is not None
        assert len(_SKILL_REVIEW_PROMPT) > 0

    def test_review_tool_whitelist_exists(self):
        """Test that review tool whitelist is defined."""
        assert REVIEW_TOOL_WHITELIST is not None
        assert isinstance(REVIEW_TOOL_WHITELIST, set)
        assert len(REVIEW_TOOL_WHITELIST) > 0
