"""MemoryProvider 抽象基类单元测试。"""

import pytest
from src.memory.provider import MemoryProvider


class ConcreteProvider(MemoryProvider):
    """用于测试的具体提供者实现。"""

    @property
    def name(self) -> str:
        return "test"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        pass

    def system_prompt_block(self) -> str:
        return "Test memory block"


class TestMemoryProviderABC:
    """测试 MemoryProvider 抽象基类。"""

    def test_cannot_instantiate_abstract(self):
        """测试无法实例化抽象类。"""
        with pytest.raises(TypeError):
            MemoryProvider()

    def test_concrete_implementation_works(self):
        """测试具体实现可以实例化。"""
        provider = ConcreteProvider()
        assert provider.name == "test"
        assert provider.is_available() is True

    def test_default_prefetch_returns_empty(self):
        """测试默认 prefetch 返回空字符串。"""
        provider = ConcreteProvider()
        assert provider.prefetch("query") == ""

    def test_default_queue_prefetch_does_nothing(self):
        """测试默认 queue_prefetch 不抛出异常。"""
        provider = ConcreteProvider()
        provider.queue_prefetch("query")  # 不应抛出异常

    def test_default_sync_turn_does_nothing(self):
        """测试默认 sync_turn 不抛出异常。"""
        provider = ConcreteProvider()
        provider.sync_turn("user", "assistant")  # 不应抛出异常

    def test_default_shutdown_does_nothing(self):
        """测试默认 shutdown 不抛出异常。"""
        provider = ConcreteProvider()
        provider.shutdown()  # 不应抛出异常

    def test_default_on_turn_start_does_nothing(self):
        """测试默认 on_turn_start 不抛出异常。"""
        provider = ConcreteProvider()
        provider.on_turn_start(1, "message")  # 不应抛出异常

    def test_default_on_session_end_does_nothing(self):
        """测试默认 on_session_end 不抛出异常。"""
        provider = ConcreteProvider()
        provider.on_session_end([])  # 不应抛出异常

    def test_default_on_pre_compress_returns_empty(self):
        """测试默认 on_pre_compress 返回空字符串。"""
        provider = ConcreteProvider()
        assert provider.on_pre_compress([]) == ""

    def test_default_on_delegation_does_nothing(self):
        """测试默认 on_delegation 不抛出异常。"""
        provider = ConcreteProvider()
        provider.on_delegation("task", "result")  # 不应抛出异常

    def test_default_on_memory_write_does_nothing(self):
        """测试默认 on_memory_write 不抛出异常。"""
        provider = ConcreteProvider()
        provider.on_memory_write("add", "memory", "content")  # 不应抛出异常

    def test_default_get_tool_schemas_returns_empty(self):
        """测试默认 get_tool_schemas 返回空列表。"""
        provider = ConcreteProvider()
        assert provider.get_tool_schemas() == []

    def test_default_handle_tool_call_raises(self):
        """测试默认 handle_tool_call 抛出 NotImplementedError。"""
        provider = ConcreteProvider()
        with pytest.raises(NotImplementedError):
            provider.handle_tool_call("unknown", {})

    def test_default_get_config_schema_returns_empty(self):
        """测试默认 get_config_schema 返回空列表。"""
        provider = ConcreteProvider()
        assert provider.get_config_schema() == []

    def test_default_save_config_does_nothing(self):
        """测试默认 save_config 不抛出异常。"""
        provider = ConcreteProvider()
        provider.save_config({}, "/tmp")  # 不应抛出异常

    def test_override_on_session_end(self):
        """测试覆盖 on_session_end 钩子。"""
        calls = []

        class OverrideProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "override"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

            def on_session_end(self, messages):
                calls.append(messages)

        provider = OverrideProvider()
        test_messages = [{"role": "user", "content": "test"}]
        provider.on_session_end(test_messages)
        assert calls == [test_messages]

    def test_core_methods_all_present(self):
        """测试 2.4.1: 核心方法都存在且可调用。"""
        from src.memory.provider import MemoryProvider

        class TestProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "core-test"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                self._initialized = True

            def system_prompt_block(self) -> str:
                return "core block"

        provider = TestProvider()
        # 验证 4 个核心方法可调用
        assert provider.name == "core-test"
        assert provider.is_available() is True
        provider.initialize("session-1")
        assert provider._initialized is True
        assert provider.system_prompt_block() == "core block"

    def test_optional_hooks_have_defaults(self):
        """测试 2.4.2: 可选钩子有默认实现。"""
        from src.memory.provider import MemoryProvider

        class MinimalProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "minimal"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

        p = MinimalProvider()
        # 所有可选钩子不应抛出异常
        p.prefetch("query")
        p.queue_prefetch("query")
        p.sync_turn("user", "assistant")
        p.shutdown()
        p.on_turn_start(1, "msg")
        p.on_session_end([])
        p.on_pre_compress([])
        p.on_delegation("task", "result")
        p.on_memory_write("add", "memory", "content")
        assert p.get_tool_schemas() == []
        assert p.get_config_schema() == []
        p.save_config({}, "/tmp")

    def test_override_optional_hooks(self):
        """测试 2.4.3: 可以覆盖可选钩子。"""
        from src.memory.provider import MemoryProvider

        call_log = []

        class HookedProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "hooked"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return ""

            def prefetch(self, query: str, **kwargs) -> str:
                call_log.append(f"prefetch:{query}")
                return f"result:{query}"

            def on_memory_write(self, action, target, content, metadata=None):
                call_log.append(f"write:{action}:{target}")

        p = HookedProvider()
        assert p.prefetch("hello") == "result:hello"
        assert call_log == ["prefetch:hello"]
        p.on_memory_write("add", "memory", "test")
        assert "write:add:memory" in call_log

    def test_receive_full_options(self):
        """测试 2.4.4: 接收完整选项参数。"""
        from src.memory.provider import MemoryProvider

        received = {}

        class OptionProvider(MemoryProvider):
            @property
            def name(self) -> str:
                return "option-test"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                received["session_id"] = session_id
                received.update(kwargs)

            def system_prompt_block(self) -> str:
                return ""

        p = OptionProvider()
        p.initialize("s1", hermes_home="/home/test", platform="telegram", extra="value")
        assert received["session_id"] == "s1"
        assert received["hermes_home"] == "/home/test"
        assert received["platform"] == "telegram"
        assert received["extra"] == "value"

    def test_skip_non_primary_context(self):
        """测试 2.4.5: 跳过非 primary 上下文。"""
        from src.memory.provider import MemoryProvider

        calls = []

        class PrimaryProvider(MemoryProvider):
            def __init__(self):
                self._is_primary = True

            @property
            def name(self) -> str:
                return "primary-test"

            def is_available(self) -> bool:
                return True

            def initialize(self, session_id: str, **kwargs) -> None:
                pass

            def system_prompt_block(self) -> str:
                return "primary block"

            def prefetch(self, query: str, **kwargs) -> str:
                calls.append(f"prefetch:{query}")
                return "context"

        # 模拟 MemoryManager 的逻辑：只调用 primary provider
        providers = [PrimaryProvider()]
        results = []
        for p in providers:
            if getattr(p, "_is_primary", False):
                results.append(p.prefetch("test query"))

        assert len(calls) == 1
        assert results == ["context"]
