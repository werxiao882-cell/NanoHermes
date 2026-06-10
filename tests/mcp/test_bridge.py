"""桥接层单元测试"""

import pytest
from pydantic import BaseModel, Field
from src.mcp.bridge import (
    bridge_tool,
    bridge_tool_with_schema,
    format_success_response,
    format_error_response,
    pydantic_to_json_schema,
)


# 测试用 Pydantic model
class SampleParams(BaseModel):
    name: str = Field(description="名称")
    count: int = Field(description="数量")


def sample_tool_fn(name: str, count: int) -> str:
    """示例工具函数"""
    return f"{name}: {count}"


async def sample_async_tool_fn(data: str) -> str:
    """示例异步工具函数"""
    return f"processed: {data}"


class TestFormatSuccessResponse:
    def test_string_result(self):
        result = format_success_response("hello")
        assert result["isError"] is False
        assert result["content"][0]["text"] == "hello"

    def test_non_string_result(self):
        result = format_success_response({"key": "value"})
        assert result["isError"] is False
        assert "key" in result["content"][0]["text"]


class TestFormatErrorResponse:
    def test_error_message(self):
        error = ValueError("test error")
        result = format_error_response(error)
        assert result["isError"] is True
        assert "test error" in result["content"][0]["text"]


class TestPydanticToJsonSchema:
    def test_conversion(self):
        schema = pydantic_to_json_schema(SampleParams)
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "count" in schema["properties"]


class TestBridgeTool:
    @pytest.mark.asyncio
    async def test_sync_tool(self):
        wrapped = bridge_tool(sample_tool_fn)
        result = await wrapped(name="test", count=5)
        assert result["isError"] is False

    @pytest.mark.asyncio
    async def test_async_tool(self):
        wrapped = bridge_tool(sample_async_tool_fn)
        result = await wrapped(data="input")
        assert result["isError"] is False

    @pytest.mark.asyncio
    async def test_error_handling(self):
        def failing_tool():
            raise RuntimeError("tool failed")

        wrapped = bridge_tool(failing_tool)
        result = await wrapped()
        assert result["isError"] is True


class TestBridgeToolWithSchema:
    def test_with_pydantic(self):
        name, fn, schema = bridge_tool_with_schema(sample_tool_fn, SampleParams)
        assert name == "sample-tool-fn"
        assert "properties" in schema

    def test_without_pydantic(self):
        name, fn, schema = bridge_tool_with_schema(sample_tool_fn)
        assert "properties" in schema
        assert "name" in schema["properties"]
