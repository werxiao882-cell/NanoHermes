"""End-to-end test: todo tool functionality."""

import json

import pytest


@pytest.fixture(autouse=True)
def _setup_todo_tool():
    """Setup and register todo tool before each test."""
    from src.tools.core.registry import ToolRegistry
    from src.tools.impls.todo_tool import reset_todo_store

    ToolRegistry.clear()
    reset_todo_store()

    # Re-import module to trigger auto-registration
    import importlib
    import src.tools.impls.todo_tool
    importlib.reload(src.tools.impls.todo_tool)

    yield

    ToolRegistry.clear()
    reset_todo_store()


def test_todo_tool_read_empty():
    """Test reading todo when list is empty."""
    from src.tools.core.dispatcher import dispatch

    result = dispatch("todo", {})
    data = json.loads(result)

    assert data["todos"] == []
    assert data["summary"]["total"] == 0
    assert data["summary"]["pending"] == 0
    assert data["summary"]["in_progress"] == 0
    assert data["summary"]["completed"] == 0
    assert data["summary"]["cancelled"] == 0

    print("\n[1] Test read empty todo list...")
    print(f"    Result: {data}")
    print("    PASSED")


def test_todo_tool_write_replace():
    """Test writing todos in replace mode."""
    from src.tools.core.dispatcher import dispatch

    todos = [
        {"id": "1", "content": "Write unit tests", "status": "pending"},
        {"id": "2", "content": "Update documentation", "status": "pending"},
        {"id": "3", "content": "Review PR", "status": "in_progress"},
    ]

    result = dispatch("todo", {"todos": todos, "merge": False})
    data = json.loads(result)

    assert len(data["todos"]) == 3
    assert data["todos"][0]["id"] == "1"
    assert data["todos"][0]["status"] == "pending"
    assert data["todos"][2]["status"] == "in_progress"
    assert data["summary"]["total"] == 3
    assert data["summary"]["pending"] == 2
    assert data["summary"]["in_progress"] == 1

    print("\n[2] Test write todos (replace mode)...")
    print(f"    Created {data['summary']['total']} tasks")
    print("    PASSED")


def test_todo_tool_merge_update():
    """Test merging todos - update existing and add new."""
    from src.tools.core.dispatcher import dispatch

    # First, create initial list
    initial = [
        {"id": "1", "content": "Task A", "status": "pending"},
        {"id": "2", "content": "Task B", "status": "pending"},
    ]
    dispatch("todo", {"todos": initial, "merge": False})

    # Merge: update task 1, add task 3
    updates = [
        {"id": "1", "content": "Task A (updated)", "status": "in_progress"},
        {"id": "3", "content": "Task C", "status": "pending"},
    ]
    result = dispatch("todo", {"todos": updates, "merge": True})
    data = json.loads(result)

    assert len(data["todos"]) == 3
    # Task 1 should be updated
    task1 = next(t for t in data["todos"] if t["id"] == "1")
    assert task1["content"] == "Task A (updated)"
    assert task1["status"] == "in_progress"
    # Task 2 should remain
    task2 = next(t for t in data["todos"] if t["id"] == "2")
    assert task2["content"] == "Task B"
    assert task2["status"] == "pending"
    # Task 3 should be added
    task3 = next(t for t in data["todos"] if t["id"] == "3")
    assert task3["content"] == "Task C"

    print("\n[3] Test merge update...")
    print(f"    Updated 1 task, added 1 new task, total: {data['summary']['total']}")
    print("    PASSED")


def test_todo_tool_status_transitions():
    """Test task status transitions."""
    from src.tools.core.dispatcher import dispatch

    # Create a task
    dispatch("todo", {"todos": [{"id": "1", "content": "Test task", "status": "pending"}], "merge": False})

    # Update to in_progress
    result = dispatch("todo", {"todos": [{"id": "1", "content": "Test task", "status": "in_progress"}], "merge": True})
    data = json.loads(result)
    assert data["todos"][0]["status"] == "in_progress"
    assert data["summary"]["in_progress"] == 1

    # Update to completed
    result = dispatch("todo", {"todos": [{"id": "1", "content": "Test task", "status": "completed"}], "merge": True})
    data = json.loads(result)
    assert data["todos"][0]["status"] == "completed"
    assert data["summary"]["completed"] == 1

    print("\n[4] Test status transitions...")
    print(f"    pending -> in_progress -> completed")
    print("    PASSED")


def test_todo_tool_cancel_task():
    """Test cancelling a task."""
    from src.tools.core.dispatcher import dispatch

    # Create and cancel a task
    dispatch("todo", {"todos": [{"id": "1", "content": "Will cancel this", "status": "pending"}], "merge": False})
    result = dispatch("todo", {"todos": [{"id": "1", "content": "Will cancel this", "status": "cancelled"}], "merge": True})
    data = json.loads(result)

    assert data["todos"][0]["status"] == "cancelled"
    assert data["summary"]["cancelled"] == 1

    print("\n[5] Test cancel task...")
    print(f"    Task cancelled successfully")
    print("    PASSED")


def test_todo_tool_invalid_status():
    """Test that invalid status defaults to pending."""
    from src.tools.core.dispatcher import dispatch

    result = dispatch("todo", {"todos": [{"id": "1", "content": "Bad status", "status": "invalid_status"}], "merge": False})
    data = json.loads(result)

    assert data["todos"][0]["status"] == "pending"

    print("\n[6] Test invalid status handling...")
    print(f"    Invalid status defaulted to 'pending'")
    print("    PASSED")


def test_todo_tool_deduplication():
    """Test that duplicate IDs are deduplicated."""
    from src.tools.core.dispatcher import dispatch

    # Write same ID twice - should keep last
    todos = [
        {"id": "1", "content": "First version", "status": "pending"},
        {"id": "1", "content": "Second version", "status": "completed"},
    ]
    result = dispatch("todo", {"todos": todos, "merge": False})
    data = json.loads(result)

    assert len(data["todos"]) == 1
    assert data["todos"][0]["content"] == "Second version"
    assert data["todos"][0]["status"] == "completed"

    print("\n[7] Test deduplication...")
    print(f"    Duplicate IDs merged, kept last version")
    print("    PASSED")


def test_todo_tool_format_for_display():
    """Test formatting todos for display."""
    from src.tools.impls.todo_tool import get_todo_store

    store = get_todo_store()
    store.write([
        {"id": "1", "content": "Completed task", "status": "completed"},
        {"id": "2", "content": "In progress task", "status": "in_progress"},
        {"id": "3", "content": "Pending task", "status": "pending"},
        {"id": "4", "content": "Cancelled task", "status": "cancelled"},
    ])

    formatted = store.format_for_display()
    assert "[x]" in formatted  # completed
    assert "[>]" in formatted  # in_progress
    assert "[ ]" in formatted  # pending
    assert "[~]" in formatted  # cancelled

    print("\n[8] Test format for display...")
    print(f"    Formatted output:\n{formatted}")
    print("    PASSED")


def test_todo_tool_full_workflow():
    """Test complete todo workflow: create, update, complete."""
    from src.tools.core.dispatcher import dispatch

    print("\n[9] Test complete workflow...")

    # Step 1: Create initial plan
    plan = [
        {"id": "1", "content": "Analyze requirements", "status": "pending"},
        {"id": "2", "content": "Design solution", "status": "pending"},
        {"id": "3", "content": "Implement code", "status": "pending"},
        {"id": "4", "content": "Write tests", "status": "pending"},
    ]
    result = dispatch("todo", {"todos": plan, "merge": False})
    data = json.loads(result)
    assert data["summary"]["total"] == 4
    print(f"    Step 1: Created {data['summary']['total']} tasks")

    # Step 2: Start first task
    result = dispatch("todo", {"todos": [{"id": "1", "content": "Analyze requirements", "status": "in_progress"}], "merge": True})
    data = json.loads(result)
    assert data["summary"]["in_progress"] == 1
    print(f"    Step 2: Started task 1")

    # Step 3: Complete first task, start second
    result = dispatch("todo", {
        "todos": [
            {"id": "1", "content": "Analyze requirements", "status": "completed"},
            {"id": "2", "content": "Design solution", "status": "in_progress"},
        ],
        "merge": True,
    })
    data = json.loads(result)
    assert data["summary"]["completed"] == 1
    assert data["summary"]["in_progress"] == 1
    print(f"    Step 3: Completed task 1, started task 2")

    # Step 4: Read current list
    result = dispatch("todo", {})
    data = json.loads(result)
    assert data["summary"]["total"] == 4
    print(f"    Step 4: Read list, total tasks: {data['summary']['total']}")

    # Step 5: Complete all remaining tasks
    remaining = [
        {"id": "2", "content": "Design solution", "status": "completed"},
        {"id": "3", "content": "Implement code", "status": "completed"},
        {"id": "4", "content": "Write tests", "status": "completed"},
    ]
    result = dispatch("todo", {"todos": remaining, "merge": True})
    data = json.loads(result)
    assert data["summary"]["completed"] == 4
    assert data["summary"]["pending"] == 0
    assert data["summary"]["in_progress"] == 0
    print(f"    Step 5: All tasks completed!")

    print("    PASSED")


def test_todo_tool_integration_with_conversation_loop():
    """Test todo tool works within conversation loop."""
    from src.tools.core.registry import ToolRegistry
    from src.tools.core.dispatcher import dispatch
    from src.conversation.loop import ConversationLoop

    print("\n[10] Test integration with conversation loop...")

    # Mock model that uses todo tool
    call_count = 0

    def mock_call(messages, tools):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call: create todo list
            return {
                "content": None,
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "todo",
                        "arguments": json.dumps({
                            "todos": [
                                {"id": "1", "content": "Plan project", "status": "pending"},
                                {"id": "2", "content": "Execute plan", "status": "pending"},
                            ],
                            "merge": False,
                        }),
                    },
                }],
                "reasoning": "Creating todo list for the project.",
                "raw_response": {"id": "mock_1"},
                "request_body": {"messages": messages},
            }
        else:
            # Second call: respond after tool execution
            return {
                "content": "I've created a todo list with 2 tasks.",
                "tool_calls": None,
                "reasoning": "Todo list created successfully.",
                "raw_response": {"id": "mock_2"},
                "request_body": {"messages": messages},
            }

    loop = ConversationLoop(
        max_iterations=5,
        model_call=mock_call,
        tool_dispatch=dispatch,
        debug=False,
    )

    result = loop.run([{"role": "user", "content": "Help me plan this project"}])

    assert call_count == 2
    assert "todo list" in result["final_response"].lower()

    # Verify todo was actually created
    store_result = dispatch("todo", {})
    store_data = json.loads(store_result)
    assert store_data["summary"]["total"] == 2

    print(f"    Conversation completed in {result['iterations']} iterations")
    print(f"    Todo list has {store_data['summary']['total']} tasks")
    print("    PASSED")

