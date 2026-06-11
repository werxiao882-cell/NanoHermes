"""Real end-to-end test: todo tool with actual LLM conversation.

This test starts the main conversation loop, simulates user input,
and verifies the todo tool works correctly with real LLM responses.

Requires valid API key in .env file.
"""

import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()


@pytest.mark.skipif(
    not os.environ.get("DASHSCOPE_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
    reason="Requires valid API key (DASHSCOPE_API_KEY or OPENAI_API_KEY)",
)
def test_todo_tool_real_conversation():
    """Test todo tool with real LLM conversation."""
    from src.config import load_config, get_api_key, get_base_url
    from openai import OpenAI
    from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
    from src.tools.core.registry import ToolRegistry
    from src.tools.core.dispatcher import dispatch
    from src.tools.impls.todo_tool import reset_todo_store
    from src.conversation.loop import ConversationLoop

    # Reset todo store
    reset_todo_store()
    ToolRegistry.clear()

    # Re-import todo_tool to trigger registration after clear
    import importlib
    import src.tools.todo_tool
    importlib.reload(src.tools.todo_tool)

    # Load config
    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = config.model.name

    if not api_key:
        pytest.skip("No API key configured")

    print(f"\n[Setup] Model: {model}")
    print(f"[Setup] Base URL: {base_url}")

    # Create real model caller
    client = OpenAI(api_key=api_key, base_url=base_url)
    provider_client = ProviderOpenAIClient(client, model)
    model_caller = provider_client.build_caller()

    # Initialize ALL tools (including todo)
    ToolRegistry.init_all_tools()
    tool_schemas = ToolRegistry.get_tool_schemas()

    # Verify todo tool is registered
    todo_tool = ToolRegistry.get_tool("todo")
    if todo_tool is None:
        print(f"[Warning] Todo tool not registered! Registered tools: {[t.name for t in ToolRegistry.get_all_tools()]}")
        pytest.skip("Todo tool not registered")

    print(f"\n[1] Testing todo tool with real LLM...")
    print(f"[Info] Total tools registered: {len(ToolRegistry.get_all_tools())}")

    # Create conversation loop
    loop = ConversationLoop(
        max_iterations=10,
        model_call=model_caller,
        tool_dispatch=dispatch,
        debug=True,
    )

    # Simulate user asking to plan a project
    messages = [
        {
            "role": "user",
            "content": "帮我规划一个Python项目，包含需求分析、设计、开发、测试四个阶段。请使用 todo 工具创建任务列表。"
        }
    ]

    print(f"\n[User] {messages[0]['content']}")
    print("\n[LLM Processing...]")

    # Run conversation
    result = loop.run(messages=messages, tools=tool_schemas)

    print(f"\n[Assistant] {result['final_response']}")
    print(f"\n[Iterations] {result['iterations']}")

    # Verify todo was created
    todo_result = dispatch("todo", {})
    todo_data = json.loads(todo_result)

    print(f"\n[Todo List Summary]")
    print(f"  Total tasks: {todo_data['summary']['total']}")
    print(f"  Pending: {todo_data['summary']['pending']}")
    print(f"  In Progress: {todo_data['summary']['in_progress']}")
    print(f"  Completed: {todo_data['summary']['completed']}")

    # Assertions
    assert todo_data["summary"]["total"] >= 4, f"Expected at least 4 tasks, got {todo_data['summary']['total']}"
    assert len(todo_data["todos"]) >= 4, f"Expected at least 4 todo items, got {len(todo_data['todos'])}"

    print("\n[2] Testing status update...")

    # Update first task to in_progress
    if todo_data["todos"]:
        first_task = todo_data["todos"][0]
        update_result = dispatch("todo", {
            "todos": [{
                "id": first_task["id"],
                "content": first_task["content"],
                "status": "in_progress"
            }],
            "merge": True
        })
        update_data = json.loads(update_result)

        # Verify update
        updated_task = next(t for t in update_data["todos"] if t["id"] == first_task["id"])
        assert updated_task["status"] == "in_progress", f"Task status not updated: {updated_task['status']}"

        print(f"  Updated task '{first_task['id']}' to in_progress")

    print("\n[3] Testing merge mode...")

    # Add a new task using merge
    add_result = dispatch("todo", {
        "todos": [{
            "id": "new_task",
            "content": "部署到生产环境",
            "status": "pending"
        }],
        "merge": True
    })
    add_data = json.loads(add_result)

    # Verify new task added
    new_task = next((t for t in add_data["todos"] if t["id"] == "new_task"), None)
    assert new_task is not None, "New task not added via merge"
    assert new_task["content"] == "部署到生产环境"

    print(f"  Added new task via merge, total: {add_data['summary']['total']}")

    print("\n" + "=" * 60)
    print("Real end-to-end todo tool test PASSED!")
    print("=" * 60)


@pytest.mark.skipif(
    not os.environ.get("DASHSCOPE_API_KEY") and not os.environ.get("OPENAI_API_KEY"),
    reason="Requires valid API key (DASHSCOPE_API_KEY or OPENAI_API_KEY)",
)
def test_todo_tool_complex_workflow():
    """Test complex todo workflow with real LLM."""
    from src.config import load_config, get_api_key, get_base_url
    from openai import OpenAI
    from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient
    from src.tools.core.registry import ToolRegistry
    from src.tools.core.dispatcher import dispatch
    from src.tools.impls.todo_tool import reset_todo_store
    from src.conversation.loop import ConversationLoop

    # Reset
    reset_todo_store()
    ToolRegistry.clear()

    # Load config
    config = load_config()
    api_key = get_api_key(config)
    base_url = get_base_url(config)
    model = config.model.name

    if not api_key:
        pytest.skip("No API key configured")

    print(f"\n[Setup] Model: {model}")

    # Create real model caller
    client = OpenAI(api_key=api_key, base_url=base_url)
    provider_client = ProviderOpenAIClient(client, model)
    model_caller = provider_client.build_caller()

    # Initialize tools
    ToolRegistry.init_all_tools()
    tool_schemas = ToolRegistry.get_tool_schemas()

    print(f"\n[1] Creating complex task plan...")

    loop = ConversationLoop(
        max_iterations=10,
        model_call=model_caller,
        tool_dispatch=dispatch,
        debug=True,
    )

    messages = [
        {
            "role": "user",
            "content": "我需要开发一个用户管理系统。请创建详细的任务列表，包括数据库设计、API开发、前端开发、测试等。使用 todo 工具管理。"
        }
    ]

    print(f"\n[User] {messages[0]['content']}")
    print("\n[LLM Processing...]")

    result = loop.run(messages=messages, tools=tool_schemas)

    print(f"\n[Assistant] {result['final_response']}")

    # Verify todo
    todo_result = dispatch("todo", {})
    todo_data = json.loads(todo_result)

    print(f"\n[Todo List]")
    for task in todo_data["todos"]:
        print(f"  [{task['status']}] {task['id']}: {task['content']}")

    assert todo_data["summary"]["total"] >= 5, f"Expected at least 5 tasks, got {todo_data['summary']['total']}"

    print("\n[2] Completing tasks...")

    # Complete first 2 tasks
    for i in range(min(2, len(todo_data["todos"]))):
        task = todo_data["todos"][i]
        dispatch("todo", {
            "todos": [{
                "id": task["id"],
                "content": task["content"],
                "status": "completed"
            }],
            "merge": True
        })
        print(f"  Completed task: {task['content']}")

    # Verify completion
    final_result = dispatch("todo", {})
    final_data = json.loads(final_result)

    completed_count = final_data["summary"]["completed"]
    assert completed_count >= 2, f"Expected at least 2 completed tasks, got {completed_count}"

    print(f"\n  Completed tasks: {completed_count}")

    print("\n" + "=" * 60)
    print("Complex workflow test PASSED!")
    print("=" * 60)

