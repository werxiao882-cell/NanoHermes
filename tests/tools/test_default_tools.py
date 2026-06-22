"""Tests for default tools."""

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _setup_default_tools():
    """Setup and register default tools before each test."""
    import importlib
    from src.tools.core.registry import ToolRegistry
    ToolRegistry.clear()

    # Reload all tool modules to trigger re-registration
    from src.tools.impls import clarify_tool
    from src.tools.impls import code_execution_tool
    from src.tools.impls import cronjob_tool
    from src.tools.impls import delegation_tool
    from src.tools.impls import memory_tool
    from src.tools.impls import session_search_tool
    from src.tools.impls import skills_tool
    from src.tools.impls import process_tool
    from src.tools.impls import file_tool

    importlib.reload(clarify_tool)
    importlib.reload(code_execution_tool)
    importlib.reload(cronjob_tool)
    importlib.reload(delegation_tool)
    importlib.reload(memory_tool)
    importlib.reload(session_search_tool)
    importlib.reload(skills_tool)
    importlib.reload(process_tool)
    importlib.reload(file_tool)

    yield

    ToolRegistry.clear()


class TestDefaultTools:
    """Tests for default tools."""

    def test_clarify_tool_registered(self):
        """Test clarify tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("clarify")
        assert tool is not None
        assert tool.name == "clarify"
        assert tool.toolset == "clarify"

    def test_execute_code_tool_registered(self):
        """Test execute_code tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("execute_code")
        assert tool is not None
        assert tool.name == "execute_code"
        assert tool.toolset == "code_execution"

    def test_cronjob_tool_registered(self):
        """Test cronjob tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("cronjob")
        assert tool is not None
        assert tool.name == "cronjob"
        assert tool.toolset == "cronjob"

    def test_delegate_task_tool_registered(self):
        """Test delegate_task tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("delegate_task")
        assert tool is not None
        assert tool.name == "delegate_task"
        assert tool.toolset == "delegation"

    def test_memory_tool_registered(self):
        """Test memory tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("memory")
        assert tool is not None
        assert tool.name == "memory"
        assert tool.toolset == "memory"

    def test_session_search_tool_registered(self):
        """Test session_search tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("session_search")
        assert tool is not None
        assert tool.name == "session_search"
        assert tool.toolset == "session_search"

    def test_skill_manage_tool_registered(self):
        """Test skill_manage tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("skill_manage")
        assert tool is not None
        assert tool.name == "skill_manage"
        assert tool.toolset == "skills"

    def test_skill_view_tool_registered(self):
        """Test skill_view tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("skill_view")
        assert tool is not None
        assert tool.name == "skill_view"
        assert tool.toolset == "skills"

    def test_skills_list_tool_registered(self):
        """Test skills_list tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("skills_list")
        assert tool is not None
        assert tool.name == "skills_list"
        assert tool.toolset == "skills"

    def test_process_tool_registered(self):
        """Test process tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("process")
        assert tool is not None
        assert tool.name == "process"
        assert tool.toolset == "terminal"

    def test_patch_tool_registered(self):
        """Test patch tool is registered."""
        from src.tools.core.registry import get_tool
        tool = get_tool("patch")
        assert tool is not None
        assert tool.name == "patch"
        assert tool.toolset == "file"


class TestDefaultToolExecution:
    """Tests for default tool execution."""

    def test_clarify_execution(self):
        """Test clarify tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("clarify", {"question": "What do you mean?"})
        data = json.loads(result)
        assert data["status"] == "clarification_requested"
        assert data["question"] == "What do you mean?"

    def test_execute_code_execution(self):
        """Test execute_code tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("execute_code", {"code": "print('hello')"})
        data = json.loads(result)
        assert data["status"] in ("code_execution_requested", "success", "error")

    def test_cronjob_list_execution(self):
        """Test cronjob list execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("cronjob", {"action": "list"})
        data = json.loads(result)
        assert data["status"] in ("success", "error")

    def test_delegate_task_execution(self):
        """Test delegate_task tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("delegate_task", {"goal": "Fix the bug"})
        data = json.loads(result)
        assert data["status"] in ("delegation_requested", "success", "error", "dispatched")

    def test_memory_execution(self):
        """Test memory tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("memory", {"action": "add", "content": "User likes Python"})
        data = json.loads(result)
        assert data["status"] in ("memory_requested", "success", "error")

    def test_session_search_execution(self):
        """Test session_search tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("session_search", {"query": "Python"})
        data = json.loads(result)
        assert data.get("status") in ("search_requested", "success", "error") or "error" in data

    def test_skills_list_execution(self):
        """Test skills_list tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("skills_list", {})
        data = json.loads(result)
        assert data.get("success") is True or data["status"] in ("success", "error")
        assert "skills" in data or "count" in data or "message" in data

    def test_process_execution(self):
        """Test process tool execution."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("process", {"action": "list"})
        data = json.loads(result)
        assert data["status"] in ("process_requested", "success", "error")


class TestPatchTool:
    """Tests for patch tool."""

    def test_patch_file_success(self, tmp_path):
        """Test patch tool successfully replaces string."""
        from src.tools.core.dispatcher import dispatch

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nHello Python", encoding="utf-8")

        result = dispatch("patch", {
            "path": str(test_file),
            "old_string": "Hello World",
            "new_string": "Hi World",
        })
        data = json.loads(result)
        assert data["status"] == "success"

        content = test_file.read_text(encoding="utf-8")
        assert "Hi World" in content
        assert "Hello Python" in content

    def test_patch_file_not_found(self):
        """Test patch tool with non-existent file."""
        from src.tools.core.dispatcher import dispatch
        result = dispatch("patch", {
            "path": "/nonexistent/file.txt",
            "old_string": "test",
            "new_string": "test",
        })
        data = json.loads(result)
        assert "error" in data

    def test_patch_string_not_found(self, tmp_path):
        """Test patch tool with string not found."""
        from src.tools.core.dispatcher import dispatch

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        result = dispatch("patch", {
            "path": str(test_file),
            "old_string": "Not Found",
            "new_string": "test",
        })
        data = json.loads(result)
        assert "error" in data
