"""Tests for todo tool."""

import json

import pytest

from src.tools.todo_tools import (
    TodoStore,
    todo_tool,
    get_todo_store,
    reset_todo_store,
)


@pytest.fixture(autouse=True)
def _reset_todo():
    """Reset todo store before and after each test."""
    reset_todo_store()
    yield
    reset_todo_store()


class TestTodoStore:
    """Tests for TodoStore class."""

    def test_empty_store(self):
        """Test that a new store is empty."""
        store = TodoStore()
        assert store.read() == []
        assert not store.has_items()

    def test_write_replaces_list(self):
        """Test that write replaces the entire list."""
        store = TodoStore()
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "pending"},
        ]
        store.write(todos)
        assert len(store.read()) == 2

        # Write new list
        new_todos = [{"id": "3", "content": "Task 3", "status": "pending"}]
        store.write(new_todos)
        assert len(store.read()) == 1
        assert store.read()[0]["id"] == "3"

    def test_write_merges_list(self):
        """Test that write with merge=True updates existing items."""
        store = TodoStore()
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "pending"},
        ]
        store.write(todos)

        # Merge update
        merge_todos = [
            {"id": "1", "content": "Updated Task 1", "status": "in_progress"},
            {"id": "3", "content": "Task 3", "status": "pending"},
        ]
        store.write(merge_todos, merge=True)

        items = store.read()
        assert len(items) == 3
        assert items[0]["content"] == "Updated Task 1"
        assert items[0]["status"] == "in_progress"
        assert items[2]["id"] == "3"

    def test_validate_item(self):
        """Test item validation."""
        store = TodoStore()

        # Valid item
        item = store._validate({"id": "1", "content": "Task", "status": "pending"})
        assert item == {"id": "1", "content": "Task", "status": "pending"}

        # Missing id
        item = store._validate({"content": "Task", "status": "pending"})
        assert item["id"] == "?"

        # Invalid status
        item = store._validate({"id": "1", "content": "Task", "status": "invalid"})
        assert item["status"] == "pending"

        # Empty content
        item = store._validate({"id": "1", "content": "", "status": "pending"})
        assert item["content"] == "(no description)"

    def test_dedupe_by_id(self):
        """Test deduplication by id."""
        store = TodoStore()
        todos = [
            {"id": "1", "content": "First", "status": "pending"},
            {"id": "2", "content": "Second", "status": "pending"},
            {"id": "1", "content": "Updated First", "status": "in_progress"},
        ]
        deduped = store._dedupe_by_id(todos)
        assert len(deduped) == 2
        # Order is preserved by last occurrence index
        assert deduped[0]["id"] == "2"
        assert deduped[0]["content"] == "Second"
        assert deduped[1]["id"] == "1"
        assert deduped[1]["content"] == "Updated First"

    def test_format_for_display(self):
        """Test formatting for display."""
        store = TodoStore()
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "completed"},
        ]
        store.write(todos)
        display = store.format_for_display()

        assert "[ ]" in display  # pending marker
        assert "[x]" in display  # completed marker
        assert "Task 1" in display
        assert "Task 2" in display

    def test_format_empty_display(self):
        """Test formatting empty list for display."""
        store = TodoStore()
        display = store.format_for_display()
        assert "No tasks" in display


class TestTodoTool:
    """Tests for todo_tool function."""

    def test_read_empty_list(self):
        """Test reading an empty list."""
        result = json.loads(todo_tool())
        assert result["todos"] == []
        assert result["summary"]["total"] == 0

    def test_write_and_read(self):
        """Test writing and reading todos."""
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "pending"},
        ]
        result = json.loads(todo_tool(todos=todos))

        assert len(result["todos"]) == 2
        assert result["summary"]["pending"] == 2
        assert result["summary"]["total"] == 2

    def test_summary_counts(self):
        """Test summary counts are correct."""
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
            {"id": "2", "content": "Task 2", "status": "in_progress"},
            {"id": "3", "content": "Task 3", "status": "completed"},
            {"id": "4", "content": "Task 4", "status": "cancelled"},
        ]
        result = json.loads(todo_tool(todos=todos))

        assert result["summary"]["pending"] == 1
        assert result["summary"]["in_progress"] == 1
        assert result["summary"]["completed"] == 1
        assert result["summary"]["cancelled"] == 1

    def test_merge_mode(self):
        """Test merge mode updates existing items."""
        # Initial write
        todos = [
            {"id": "1", "content": "Task 1", "status": "pending"},
        ]
        todo_tool(todos=todos)

        # Merge update
        merge_todos = [
            {"id": "1", "content": "Updated Task 1", "status": "completed"},
            {"id": "2", "content": "Task 2", "status": "pending"},
        ]
        result = json.loads(todo_tool(todos=merge_todos, merge=True))

        assert len(result["todos"]) == 2
        assert result["todos"][0]["content"] == "Updated Task 1"
        assert result["todos"][0]["status"] == "completed"

    def test_global_store(self):
        """Test that global store is used."""
        todos = [{"id": "1", "content": "Task", "status": "pending"}]
        todo_tool(todos=todos)

        # Read from global store
        result = json.loads(todo_tool())
        assert len(result["todos"]) == 1


class TestTodoToolIntegration:
    """Integration tests for todo tool via dispatcher."""

    def test_todo_via_dispatcher(self):
        """Test todo tool via dispatcher."""
        from src.tools.registry import ToolRegistry
        from src.tools import todo_tools
        import importlib
        from src.tools.dispatcher import dispatch

        ToolRegistry.clear()
        importlib.reload(todo_tools)

        # Write todos
        result = dispatch("todo", {
            "todos": [
                {"id": "1", "content": "Task 1", "status": "pending"},
            ]
        })
        data = json.loads(result)
        assert data["summary"]["total"] == 1

        # Read todos
        result = dispatch("todo", {})
        data = json.loads(result)
        assert len(data["todos"]) == 1
