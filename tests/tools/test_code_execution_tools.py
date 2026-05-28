"""Tests for code execution tools module."""

import pytest
import json
from unittest.mock import patch

from src.tools.code_execution_tools import execute_code


class TestExecuteCode:
    """Tests for execute_code tool function."""

    def test_execute_code_basic(self):
        """Test basic code execution request."""
        result = json.loads(execute_code(code="print('hello')"))
        assert result["status"] == "code_execution_requested"
        assert result["language"] == "python"
        assert result["code_length"] == len("print('hello')")

    def test_execute_code_custom_language(self):
        """Test code execution with custom language."""
        result = json.loads(execute_code(code="console.log('hello')", language="javascript"))
        assert result["language"] == "javascript"

    def test_execute_code_empty_code(self):
        """Test code execution with empty code."""
        result = json.loads(execute_code(code=""))
        assert result["code_length"] == 0

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
        assert data["status"] == "code_execution_requested"
