"""ContextEngine 抽象基类单元测试。"""

import pytest
from src.compression.engine import ContextEngine


class ConcreteContextEngine(ContextEngine):
    """用于测试的具体上下文引擎实现。"""

    def update_from_response(self, response):
        pass

    def should_compress(self):
        return False

    def compress(self, messages):
        return {"messages": messages, "summary": "test"}


class TestContextEngineABC:
    """测试 ContextEngine 抽象基类。"""

    def test_cannot_instantiate_abstract(self):
        """测试无法实例化抽象类。"""
        with pytest.raises(TypeError):
            ContextEngine()

    def test_concrete_implementation_works(self):
        """测试具体实现可以实例化。"""
        engine = ConcreteContextEngine()
        assert engine.update_from_response({}) is None
        assert engine.should_compress() is False
        assert engine.compress([]) == {"messages": [], "summary": "test"}

    def test_default_get_tool_schemas_returns_empty(self):
        """测试默认 get_tool_schemas 返回空列表。"""
        engine = ConcreteContextEngine()
        assert engine.get_tool_schemas() == []

    def test_default_handle_tool_call_raises(self):
        """测试默认 handle_tool_call 抛出 NotImplementedError。"""
        engine = ConcreteContextEngine()
        with pytest.raises(NotImplementedError):
            engine.handle_tool_call("unknown", {})

    def test_override_tool_schemas(self):
        """测试覆盖工具 schema。"""

        class ToolEngine(ContextEngine):
            def update_from_response(self, response):
                pass

            def should_compress(self):
                return False

            def compress(self, messages):
                return {}

            def get_tool_schemas(self):
                return [{"name": "recall_context", "description": "Recall context"}]

        engine = ToolEngine()
        schemas = engine.get_tool_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "recall_context"

    def test_override_handle_tool_call(self):
        """测试覆盖工具调用处理。"""

        class ToolEngine(ContextEngine):
            def update_from_response(self, response):
                pass

            def should_compress(self):
                return False

            def compress(self, messages):
                return {}

            def handle_tool_call(self, tool_name, args):
                return f"Handled {tool_name}"

        engine = ToolEngine()
        result = engine.handle_tool_call("test_tool", {})
        assert result == "Handled test_tool"
