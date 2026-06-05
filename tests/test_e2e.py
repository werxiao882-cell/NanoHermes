"""End-to-end test: full conversation loop with tools (mock model)."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _setup_tools():
    """Setup and register all tools before each test."""
    from src.tools.registry import ToolRegistry
    ToolRegistry.clear()

    # Import modules to trigger auto-registration
    from src.tools.terminal import _register_terminal_tool
    from src.tools.file_tool import _register_file_tools

    _register_terminal_tool()
    _register_file_tools()

    yield

    ToolRegistry.clear()


def test_e2e_conversation_with_tools():
    """End-to-end test: full conversation loop with tool calls and debug mode."""
    from src.tools.registry import ToolRegistry, get_tool_schemas
    from src.tools.dispatcher import dispatch

    tools = ToolRegistry.get_all_tools()
    tool_names = [t.name for t in tools]
    print(f"\n[1] Registered tools: {tool_names}")
    assert len(tools) >= 4, f"Expected >= 4 tools, got {len(tools)}: {tool_names}"

    # Test tool dispatch with JSON args
    print("\n[2] Testing tool dispatch...")
    result = dispatch("terminal", {"command": "echo hello"})
    data = json.loads(result)
    assert "hello" in data["stdout"], f"Tool execution failed: {result}"
    print(f"    terminal: echo hello -> {data['stdout'].strip()}")

    # Test file tools
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.txt"

        result = dispatch("write_file", {"path": str(test_file), "content": "Hello World"})
        data = json.loads(result)
        assert data["status"] == "success"
        print(f"    write_file: {data['bytes_written']} bytes written")

        result = dispatch("read_file", {"path": str(test_file)})
        data = json.loads(result)
        assert "Hello World" in data["content"]
        print(f"    read_file: {data['lines_returned']} lines returned")

        result = dispatch("search_files", {"path": tmpdir, "pattern": "*.txt"})
        data = json.loads(result)
        assert data["total_found"] >= 1
        print(f"    search_files: {data['total_found']} files found")

    # Test ConversationLoop with mock model
    print("\n[3] Testing ConversationLoop...")
    from src.conversation.loop import ConversationLoop

    call_count = 0

    def mock_call(messages, tools):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "terminal",
                        "arguments": json.dumps({"command": "echo test"}),
                    },
                }],
                "reasoning": "User wants to run a command, calling terminal tool.",
                "raw_response": {"id": "mock_1"},
                "request_body": {"messages": messages},
            }
        else:
            return {
                "content": "Command executed, output is 'test'.",
                "tool_calls": None,
                "reasoning": "Tool executed, replying to user.",
                "raw_response": {"id": "mock_2"},
                "request_body": {"messages": messages},
            }

    loop = ConversationLoop(
        max_iterations=5,
        model_call=mock_call,
        tool_dispatch=dispatch,
        debug=True,
    )

    result = loop.run([{"role": "user", "content": "Run echo test"}])

    assert call_count == 2, f"Expected 2 calls, got {call_count}"
    assert "Command executed" in result["final_response"]
    assert result["iterations"] == 2
    print(f"    Response: {result['final_response']}")
    print(f"    Iterations: {result['iterations']}")

    # Test SessionDB persistence
    print("\n[4] Testing SessionDB persistence...")
    with tempfile.TemporaryDirectory() as tmpdir:
        from src.session.session_db import SessionDB

        db_path = Path(tmpdir) / "sessions.db"
        with SessionDB(db_path) as db:
            session_id = db.create_session(model="qwen3.6-plus", provider="dashscope")
            db.insert_message(session_id, "user", "Run echo test")
            db.insert_message(session_id, "assistant", result["final_response"])
            db.update_token_counts(session_id, input_tokens=100, output_tokens=50)

            messages = db.get_messages(session_id)
            assert len(messages) == 2
            session = db.get_session(session_id)
            assert session["input_tokens"] == 100
            assert session["output_tokens"] == 50
            print(f"    Session {session_id[:8]}... saved")
            print(f"    Messages: {len(messages)}, Tokens: {session['input_tokens']}+{session['output_tokens']}")

    print("\n" + "=" * 60)
    print("All end-to-end tests passed!")
    print("=" * 60)


def test_main_entry_build_model_caller():
    """Test OpenAIClient.build_caller method and entry point."""
    from unittest.mock import MagicMock
    from openai import OpenAI
    from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient

    # Create mock client
    mock_client = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.choices = [MagicMock()]
    mock_chunk.choices[0].delta.content = "Hello"
    mock_chunk.choices[0].delta.reasoning = None
    mock_chunk.choices[0].delta.tool_calls = None
    mock_chunk.usage = MagicMock()
    mock_chunk.usage.prompt_tokens = 10
    mock_chunk.usage.completion_tokens = 5

    # Mock stream response
    mock_stream = [mock_chunk]
    mock_client.chat.completions.create.return_value = iter(mock_stream)

    # Test OpenAIClient.build_caller
    provider_client = ProviderOpenAIClient(mock_client, "test-model")
    model_caller = provider_client.build_caller()
    result = model_caller([{"role": "user", "content": "Hi"}], None)

    assert result["content"] == "Hello"
    assert result["usage"]["input_tokens"] == 10
    assert result["usage"]["output_tokens"] == 5
    assert "stream" in result["request_body"]
    assert result["request_body"]["stream"] is True

    print("\n[5] Testing OpenAIClient.build_caller...")
    print(f"    Content: {result['content']}")
    print(f"    Usage: {result['usage']}")
    print("    OpenAIClient.build_caller works correctly!")

