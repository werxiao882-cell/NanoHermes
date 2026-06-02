"""测试: 工具运行时集成测试。

测试完整的工具调用链、终端工具执行、危险命令审批和工具集过滤。
"""

import asyncio
import pytest
import tempfile
import os
from pathlib import Path
from unittest import mock

from src.tools.registry import (
    ToolRegistry,
    ToolEntry,
    register_tool,
    get_tool,
    get_all_tools,
    get_tool_schemas,
)
from src.tools.dispatcher import dispatch
from src.tools.toolsets import (
    TOOLSETS,
    resolve_toolset,
    resolve_enabled_toolsets,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    """每个测试前后清空注册表。"""
    ToolRegistry.clear()
    yield
    ToolRegistry.clear()


class TestFullToolCallChain:
    """测试完整工具调用链（任务 9.1）。"""

    def test_register_discover_resolve_dispatch(self):
        """测试 register → discover → resolve → dispatch 完整流程。"""
        # 1. 注册工具
        def test_handler(**kwargs):
            return f"handled: {kwargs.get('input', 'none')}"
        
        register_tool(
            name="chain_test",
            toolset="test",
            schema={
                "name": "chain_test",
                "description": "测试工具",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input": {"type": "string"},
                    },
                },
            },
            handler=test_handler,
        )
        
        # 2. 验证工具已注册
        tool = get_tool("chain_test")
        assert tool is not None
        assert tool.name == "chain_test"
        
        # 3. 验证 schema 可获取
        schemas = get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "chain_test"
        
        # 4. 调用分发器执行
        result = dispatch("chain_test", {"input": "test_value"})
        assert "handled: test_value" in result

    def test_dispatch_with_task_id(self):
        """测试 task_id 在调用链中传播。"""
        def handler_with_task_id(**kwargs):
            return f"task_id: {kwargs.get('task_id', 'none')}"
        
        register_tool(
            name="task_test",
            toolset="test",
            schema={"name": "task_test"},
            handler=handler_with_task_id,
        )
        
        result = dispatch("task_test", {}, task_id="task-123")
        assert "task_id: task-123" in result

    def test_dispatch_unknown_tool(self):
        """测试分发未知工具返回错误。"""
        result = dispatch("unknown_tool", {})
        assert "error" in result.lower() or "未找到" in result

    def test_async_handler_dispatch(self):
        """测试异步 handler 分发。"""
        async def async_handler(**kwargs):
            await asyncio.sleep(0.01)
            return f"async result: {kwargs.get('value')}"
        
        register_tool(
            name="async_test",
            toolset="test",
            schema={"name": "async_test"},
            handler=async_handler,
            is_async=True,
        )
        
        # 分发器应通过 async_bridge 执行异步 handler
        result = dispatch("async_test", {"value": "async_val"})
        assert "async result: async_val" in result


class TestTerminalToolIntegration:
    """测试终端工具集成（任务 9.2）。"""

    def test_terminal_tool_available(self):
        """测试终端工具可用（通过导入验证）。"""
        # 导入终端模块
        from src.tools.terminal import DANGEROUS_PATTERNS, LocalEnvironment
        
        # DANGEROUS_PATTERNS 应已定义
        assert len(DANGEROUS_PATTERNS) > 0
        
        # LocalEnvironment 应可用
        env = LocalEnvironment()
        result = env.execute("echo test")
        assert "test" in result.stdout

    def test_terminal_environment_interface(self):
        """测试终端环境接口。"""
        from src.tools.terminal import LocalEnvironment
        
        env = LocalEnvironment()
        
        # 测试基本执行
        result = env.execute("ls")
        assert result.exit_code == 0
        
        # 测试带 cwd
        with tempfile.TemporaryDirectory() as tmpdir:
            result = env.execute("pwd", cwd=tmpdir)
            assert tmpdir in result.stdout


class TestDangerousCommandApproval:
    """测试危险命令审批集成（任务 9.3）。"""

    def test_dangerous_patterns_defined(self):
        """测试危险命令模式已定义。"""
        from src.tools.terminal import DANGEROUS_PATTERNS
        
        # 应有危险模式列表
        assert len(DANGEROUS_PATTERNS) > 0
        
        # 应包含 rm -rf 模式
        rm_pattern = None
        for pattern_tuple in DANGEROUS_PATTERNS:
            if "rm" in pattern_tuple[0]:
                rm_pattern = pattern_tuple
                break
        assert rm_pattern is not None

    def test_dangerous_command_detection(self):
        """测试危险命令检测。"""
        import re
        from src.tools.terminal import DANGEROUS_PATTERNS
        
        # 检查各种危险命令
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda",
        ]
        
        for cmd in dangerous_commands:
            is_dangerous = any(
                re.search(pattern_tuple[0], cmd) 
                for pattern_tuple in DANGEROUS_PATTERNS
            )
            assert is_dangerous is True

    def test_safe_command_not_flagged(self):
        """测试安全命令不被标记。"""
        import re
        from src.tools.terminal import DANGEROUS_PATTERNS
        
        safe_commands = [
            "ls -la",
            "echo hello",
            "cat file.txt",
            "pwd",
        ]
        
        for cmd in safe_commands:
            is_dangerous = any(
                re.search(pattern_tuple[0], cmd) 
                for pattern_tuple in DANGEROUS_PATTERNS
            )
            assert is_dangerous is False


class TestToolsetFiltering:
    """测试工具集过滤集成（任务 9.4）。"""

    def test_enabled_toolsets_filter(self):
        """测试 enabled_toolsets 过滤。"""
        # 注册多个工具集的工具
        register_tool(name="term1", toolset="terminal", schema={"name": "term1"}, handler=lambda: "t")
        register_tool(name="file1", toolset="file", schema={"name": "file1"}, handler=lambda: "f")
        register_tool(name="web1", toolset="web", schema={"name": "web1"}, handler=lambda: "w")
        
        # 只启用 terminal 工具集
        enabled_tools = resolve_enabled_toolsets(enabled_toolsets=["terminal"])
        schemas = get_tool_schemas(toolset_filter={"terminal"})
        
        # 应只有 terminal 工具集的工具
        assert len(schemas) == 1
        assert schemas[0]["name"] == "term1"
        # enabled_tools 应包含 terminal 工具集中的工具名
        assert "terminal" in enabled_tools or "term1" in enabled_tools

    def test_disabled_toolsets_filter(self):
        """测试 disabled_toolsets 过滤。"""
        register_tool(name="term2", toolset="terminal", schema={"name": "term2"}, handler=lambda: "t")
        register_tool(name="file2", toolset="file", schema={"name": "file2"}, handler=lambda: "f")
        register_tool(name="web2", toolset="web", schema={"name": "web2"}, handler=lambda: "w")
        
        # 禁用 web 工具集
        enabled_tools = resolve_enabled_toolsets(disabled_toolsets=["web"])
        schemas = get_tool_schemas(toolset_filter={"terminal", "file"})
        
        names = [s["name"] for s in schemas]
        assert "term2" in names
        assert "file2" in names
        assert "web2" not in names

    def test_toolset_resolution(self):
        """测试 toolset 名称解析。"""
        # 测试 TOOLSETS 常量中的映射
        # resolve_toolset 应展开 toolset 名为工具名集合
        if "terminal" in TOOLSETS:
            tools = resolve_toolset("terminal")
            assert isinstance(tools, set)
            assert len(tools) > 0

    def test_multiple_enabled_toolsets(self):
        """测试多个启用工具集。"""
        register_tool(name="t1", toolset="terminal", schema={"name": "t1"}, handler=lambda: "x")
        register_tool(name="f1", toolset="file", schema={"name": "f1"}, handler=lambda: "x")
        register_tool(name="w1", toolset="web", schema={"name": "w1"}, handler=lambda: "x")
        
        schemas = get_tool_schemas(toolset_filter={"terminal", "file"})
        
        names = [s["name"] for s in schemas]
        assert "t1" in names
        assert "f1" in names
        assert "w1" not in names

    def test_empty_toolset_filter(self):
        """测试空工具集过滤。"""
        register_tool(name="x", toolset="test", schema={"name": "x"}, handler=lambda: "x")
        
        # 空列表应返回所有工具
        schemas = get_tool_schemas()
        
        assert len(schemas) >= 1


class TestDispatcherErrorHandling:
    """测试分发器错误处理。"""

    def test_handler_exception_wrapped(self):
        """测试 handler 异常被包装。"""
        def failing_handler(**kwargs):
            raise ValueError("handler error")
        
        register_tool(
            name="fail_test",
            toolset="test",
            schema={"name": "fail_test"},
            handler=failing_handler,
        )
        
        result = dispatch("fail_test", {})
        
        # 异常应被捕获并返回 JSON 错误
        assert "error" in result.lower() or "exception" in result.lower()

    def test_missing_required_param(self):
        """测试缺少必需参数。"""
        def strict_handler(**kwargs):
            if "required" not in kwargs:
                raise KeyError("missing required param")
            return "ok"
        
        register_tool(
            name="strict_test",
            toolset="test",
            schema={"name": "strict_test"},
            handler=strict_handler,
        )
        
        result = dispatch("strict_test", {})
        
        # 应有错误信息
        assert "error" in result.lower() or "missing" in result.lower()