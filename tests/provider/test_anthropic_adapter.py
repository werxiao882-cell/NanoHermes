"""测试: Anthropic 适配器。"""

import pytest

from src.provider.anthropic_adapter import AnthropicAdapter


class TestMessageConversion:
    """测试消息格式转换。"""

    def test_convert_system_message(self):
        """测试 system message 提取为独立参数。"""
        adapter = AnthropicAdapter(client=None, model="claude-test")  # type: ignore
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        system_prompt, converted = adapter._convert_messages(messages)

        assert system_prompt == "You are a helpful assistant."
        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["content"] == "Hello!"

    def test_convert_tool_result(self):
        """测试 tool 角色消息转换为 tool_result 格式。"""
        adapter = AnthropicAdapter(client=None, model="claude-test")  # type: ignore
        messages = [
            {"role": "tool", "tool_call_id": "call_123", "content": '{"result": "ok"}'},
        ]
        _, converted = adapter._convert_messages(messages)

        assert len(converted) == 1
        assert converted[0]["role"] == "user"
        assert converted[0]["content"][0]["type"] == "tool_result"
        assert converted[0]["content"][0]["tool_use_id"] == "call_123"

    def test_convert_tool_calls_in_assistant(self):
        """测试 assistant 消息中的 tool_calls 转换。"""
        adapter = AnthropicAdapter(client=None, model="claude-test")  # type: ignore
        messages = [
            {
                "role": "assistant",
                "content": "Let me check that.",
                "tool_calls": [
                    {
                        "id": "call_456",
                        "function": {
                            "name": "search_files",
                            "arguments": '{"pattern": "*.py"}',
                        },
                    },
                ],
            },
        ]
        _, converted = adapter._convert_messages(messages)

        assert len(converted) == 1
        content_blocks = converted[0]["content"]
        assert len(content_blocks) == 2
        assert content_blocks[0]["type"] == "text"
        assert content_blocks[1]["type"] == "tool_use"
        assert content_blocks[1]["name"] == "search_files"


class TestToolConversion:
    """测试工具 schema 转换。"""

    def test_convert_openai_tool_to_anthropic(self):
        """测试 OpenAI 工具 schema 转换为 Anthropic 格式。"""
        adapter = AnthropicAdapter(client=None, model="claude-test")  # type: ignore
        tools = [
            {
                "name": "terminal",
                "description": "Execute shell commands",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                },
            },
        ]
        converted = adapter._convert_tools(tools)

        assert len(converted) == 1
        assert converted[0]["name"] == "terminal"
        assert converted[0]["description"] == "Execute shell commands"
        assert "input_schema" in converted[0]
        assert converted[0]["input_schema"]["properties"]["command"]["type"] == "string"
