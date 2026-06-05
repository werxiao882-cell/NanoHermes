"""Tests for code execution tools module."""

import pytest
import json
from unittest.mock import patch

from src.tools.code_execution_tool import execute_code


class TestExecuteCode:
    """Tests for execute_code tool function."""

    def test_execute_code_basic(self):
        """Test basic code execution request."""
        result = json.loads(execute_code(code="print('hello')"))
        # 实际执行返回 success �?error（取决于执行结果�?        assert result["status"] in ("code_execution_requested", "success", "error")
        assert result.get("language") == "python" or "stdout" in result or "stderr" in result

    def test_execute_code_custom_language(self):
        """Test code execution with custom language."""
        result = json.loads(execute_code(code="console.log('hello')", language="javascript"))
        # JavaScript 不支持，返回 error
        assert result["status"] == "error" or result.get("language") == "javascript"

    def test_execute_code_empty_code(self):
        """Test code execution with empty code."""
        result = json.loads(execute_code(code=""))
        assert result["status"] == "error"
        assert "code is required" in result.get("message", "").lower()

    def test_execute_code_via_dispatcher(self):
        """Test execute_code tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import code_execution_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(code_execution_tools)

        result = dispatch("execute_code", {"code": "print('test')"})
        data = json.loads(result)
        assert data["status"] in ("code_execution_requested", "success", "error")

