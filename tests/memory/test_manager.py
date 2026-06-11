"""MemoryManager 编排器单元测试。"""

import pytest
from src.memory.provider import MemoryProvider
from src.memory.manager import MemoryManager


class MockProvider(MemoryProvider):
    """模拟提供者用于测试。"""

    def __init__(self, name: str = "mock", fail_on: str = None):
        self._name = name
        self._fail_on = fail_on
        self._initialized = False
        self._sync_calls = []
        self._prefetch_calls = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        if self._fail_on == "initialize":
            raise RuntimeError("Initialize failed")
        self._initialized = True

    def system_prompt_block(self) -> str:
        if self._fail_on == "system_prompt_block":
            raise RuntimeError("System prompt failed")
        return f"{self._name} block"

    def prefetch(self, query: str, **kwargs) -> str:
        if self._fail_on == "prefetch":
            raise RuntimeError("Prefetch failed")
        self._prefetch_calls.append(query)
        return f"{self._name}: {query}"

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        if self._fail_on == "sync_turn":
            raise RuntimeError("Sync failed")
        self._sync_calls.append((user_content, assistant_content))

    def queue_prefetch(self, query: str, **kwargs) -> None:
        if self._fail_on == "queue_prefetch":
            raise RuntimeError("Queue prefetch failed")

    def shutdown(self) -> None:
        if self._fail_on == "shutdown":
            raise RuntimeError("Shutdown failed")


@pytest.fixture
def manager():
    """创建 MemoryManager 实例。"""
    return MemoryManager()


class TestMemoryManagerRegistration:
    """测试提供者注册。"""

    def test_register_builtin_provider(self, manager):
        """测试注册内置提供者。"""
        provider = MockProvider(name="builtin")
        manager.add_provider(provider)
        assert provider in manager.providers

    def test_register_first_external_provider(self, manager):
        """测试注册第一个外部提供者。"""
        provider = MockProvider(name="honcho")
        manager.add_provider(provider)
        assert provider in manager.providers

    def test_reject_second_external_provider(self, manager, caplog):
        """测试拒绝第二个外部提供者。"""
        provider1 = MockProvider(name="honcho")
        provider2 = MockProvider(name="mem0")
        manager.add_provider(provider1)
        manager.add_provider(provider2)

        assert provider1 in manager.providers
        assert provider2 not in manager.providers
        assert "拒绝第二个外部提供者" in caplog.text

    def test_register_multiple_builtin_providers(self, manager):
        """测试注册多个内置提供者。"""
        provider1 = MockProvider(name="builtin")
        provider2 = MockProvider(name="builtin2")
        manager.add_provider(provider1)
        manager.add_provider(provider2)

        assert len(manager.providers) == 2


class TestMemoryManagerSystemPrompt:
    """测试系统提示构建。"""

    def test_single_provider_prompt(self, manager):
        """测试单个提供者提示。"""
        provider = MockProvider(name="test")
        manager.add_provider(provider)
        result = manager.build_system_prompt()
        assert result == "test block"

    def test_multiple_providers_prompt(self, manager):
        """测试多个提供者提示（一个内置 + 一个外部）。"""
        manager.add_provider(MockProvider(name="builtin"))
        manager.add_provider(MockProvider(name="honcho"))
        result = manager.build_system_prompt()
        assert "builtin block" in result
        assert "honcho block" in result

    def test_empty_prompt_skipped(self, manager):
        """测试空提示被跳过。"""

        class EmptyProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "empty"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

        manager.add_provider(EmptyProvider())
        result = manager.build_system_prompt()
        assert result == ""


class TestMemoryManagerPrefetch:
    """测试预取功能。"""

    def test_prefetch_wraps_context(self, manager):
        """测试预取上下文包裹。"""
        provider = MockProvider(name="builtin")
        manager.add_provider(provider)
        result = manager.prefetch_all("Hello")
        assert '<memory-context provider="builtin">' in result
        assert "builtin: Hello" in result
        assert "</memory-context>" in result

    def test_prefetch_empty_skipped(self, manager):
        """测试空预取被跳过。"""

        class EmptyPrefetchProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "empty"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

            def prefetch(self, query: str, **kwargs) -> str:
                return ""

        manager.add_provider(EmptyPrefetchProvider())
        result = manager.prefetch_all("Hello")
        assert result == ""


class TestMemoryManagerFanOut:
    """测试 Fan-out 容错。"""

    def test_single_provider_sync_failure(self, manager, caplog):
        """测试单个提供者同步失败不影响其他提供者。"""
        failing = MockProvider(name="honcho", fail_on="sync_turn")
        working = MockProvider(name="builtin", fail_on=None)
        manager.add_provider(failing)
        manager.add_provider(working)

        manager.sync_all("user", "assistant")

        # working 提供者仍被调用
        assert len(working._sync_calls) == 1
        # 记录警告
        assert "sync failed" in caplog.text

    def test_all_providers_sync_success(self, manager):
        """测试所有提供者同步成功。"""
        p1 = MockProvider(name="builtin")
        p2 = MockProvider(name="honcho")
        manager.add_provider(p1)
        manager.add_provider(p2)

        manager.sync_all("user", "assistant")

        assert len(p1._sync_calls) == 1
        assert len(p2._sync_calls) == 1

    def test_single_provider_prefetch_failure(self, manager, caplog):
        """测试单个提供者预取失败不影响其他提供者。"""
        failing = MockProvider(name="honcho", fail_on="prefetch")
        working = MockProvider(name="builtin")
        manager.add_provider(failing)
        manager.add_provider(working)

        result = manager.prefetch_all("Hello")

        # working 提供者仍被调用
        assert "builtin: Hello" in result
        # 记录警告
        assert "prefetch failed" in caplog.text


class TestMemoryManagerToolRouting:
    """测试工具路由。"""

    def test_handle_tool_call(self, manager):
        """测试处理工具调用。"""

        class ToolProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "tool"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

            def get_tool_schemas(self):
                return [{"name": "custom_tool", "description": "A custom tool"}]

            def handle_tool_call(self, tool_name, args, **kwargs):
                return f"Handled {tool_name} with {args}"

        provider = ToolProvider()
        manager.add_provider(provider)

        result = manager.handle_tool_call("custom_tool", {"key": "value"})
        assert result == "Handled custom_tool with {'key': 'value'}"

    def test_handle_unknown_tool_returns_none(self, manager):
        """测试处理未知工具返回 None。"""
        result = manager.handle_tool_call("unknown", {})
        assert result is None

    def test_get_tool_schemas(self, manager):
        """测试获取工具 schema。"""
        provider = MockProvider(name="test")
        manager.add_provider(provider)
        schemas = manager.get_tool_schemas()
        assert isinstance(schemas, list)
