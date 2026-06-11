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
