"""工具输出剪枝单元测试。"""

import json
import pytest

from src.compression.pruning import (
    prune_tool_outputs,
    truncate_tool_call_args,
    _truncate_object_strings,
    TOOL_OUTPUT_PRUNE_THRESHOLD,
    TOOL_OUTPUT_PRUNE_PLACEHOLDER,
)


class TestPruneToolOutputs:
    """测试 prune_tool_outputs 函数。"""

    def test_replace_long_tool_output(self):
        """测试替换长工具输出。"""
        messages = [
            {"role": "tool", "content": "A" * (TOOL_OUTPUT_PRUNE_THRESHOLD + 100)},
        ]
        result = prune_tool_outputs(messages)
        assert result[0]["content"] == TOOL_OUTPUT_PRUNE_PLACEHOLDER

    def test_keep_short_tool_output(self):
        """测试保留短工具输出。"""
        messages = [
            {"role": "tool", "content": "Short output"},
        ]
        result = prune_tool_outputs(messages)
        assert result[0]["content"] == "Short output"

    def test_non_tool_messages_unchanged(self):
        """测试非工具消息不变。"""
        messages = [
            {"role": "user", "content": "A" * (TOOL_OUTPUT_PRUNE_THRESHOLD + 100)},
            {"role": "assistant", "content": "A" * (TOOL_OUTPUT_PRUNE_THRESHOLD + 100)},
        ]
        result = prune_tool_outputs(messages)
        assert result[0]["content"] == "A" * (TOOL_OUTPUT_PRUNE_THRESHOLD + 100)
        assert result[1]["content"] == "A" * (TOOL_OUTPUT_PRUNE_THRESHOLD + 100)


class TestTruncateToolCallArgs:
    """测试 truncate_tool_call_args 函数。"""

    def test_truncate_json_string_values(self):
        """测试截断 JSON 字符串值。"""
        args = json.dumps({"long_string": "A" * 500, "short_string": "short"})
        result = truncate_tool_call_args(args, max_chars=100)
        parsed = json.loads(result)
        assert len(parsed["long_string"]) <= 115  # 100 + "...[truncated]"
        assert parsed["short_string"] == "short"

    def test_non_json_args_unchanged(self):
        """测试非 JSON 参数不变。"""
        args = "not valid json"
        result = truncate_tool_call_args(args)
        assert result == args

    def test_nested_object_truncation(self):
        """测试嵌套对象字符串截断。"""
        args = json.dumps({
            "nested": {
                "deep": {
                    "value": "B" * 500
                }
            }
        })
        result = truncate_tool_call_args(args, max_chars=100)
        parsed = json.loads(result)
        assert len(parsed["nested"]["deep"]["value"]) <= 115

    def test_array_string_truncation(self):
        """测试数组字符串截断。"""
        args = json.dumps(["A" * 500, "B" * 500, "short"])
        result = truncate_tool_call_args(args, max_chars=100)
        parsed = json.loads(result)
        assert len(parsed[0]) <= 115
        assert len(parsed[1]) <= 115
        assert parsed[2] == "short"


class TestTruncateObjectStrings:
    """测试 _truncate_object_strings 函数。"""

    def test_string_truncation(self):
        """测试字符串截断。"""
        result = _truncate_object_strings("A" * 500, 100)
        assert len(result) == 114  # 100 + "...[truncated]"
        assert result.endswith("...[truncated]")

    def test_string_no_truncation(self):
        """测试短字符串不截断。"""
        result = _truncate_object_strings("short", 100)
        assert result == "short"

    def test_list_truncation(self):
        """测试列表截断。"""
        result = _truncate_object_strings(["A" * 500, "short"], 100)
        assert len(result[0]) <= 115
        assert result[1] == "short"

    def test_dict_truncation(self):
        """测试字典截断。"""
        result = _truncate_object_strings({"key": "A" * 500}, 100)
        assert len(result["key"]) <= 115

    def test_non_string_unchanged(self):
        """测试非字符串不变。"""
        assert _truncate_object_strings(123, 100) == 123
        assert _truncate_object_strings(True, 100) is True
        assert _truncate_object_strings(None, 100) is None
