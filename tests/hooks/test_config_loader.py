"""Hook 配置加载器单元测试。"""

from unittest.mock import patch, MagicMock

from src.conversation.events import EventBus, EventType
from src.hooks.config_loader import load_hooks_from_config, _create_handler
from src.hooks.script_hook import ScriptHook


class TestConfigLoader:
    """测试配置加载器。"""

    def test_load_empty_config(self):
        """测试空配置不报错。"""
        bus = EventBus()
        load_hooks_from_config({}, bus)
        load_hooks_from_config({"hooks": {}}, bus)

    def test_load_script_hook(self):
        """测试加载脚本 hook。"""
        bus = EventBus()
        config = {
            "hooks": {
                "model_request": [
                    {"type": "script", "path": "./validate.sh", "timeout": 30}
                ]
            }
        }
        load_hooks_from_config(config, bus)

        # 验证拦截器已注册
        assert len(bus._interceptors.get(EventType.MODEL_REQUEST, [])) == 1
        _, handler = bus._interceptors[EventType.MODEL_REQUEST][0]
        assert isinstance(handler, ScriptHook)

    def test_load_python_hook(self):
        """测试加载 Python hook。"""
        bus = EventBus()

        def dummy_handler(data, next_fn):
            next_fn()

        config = {
            "hooks": {
                "tool_start": [
                    {"type": "python", "module": "src.hooks.dangerous_command_guard",
                     "function": "dangerous_command_guard", "priority": 5}
                ]
            }
        }
        load_hooks_from_config(config, bus)

        # 验证拦截器已注册
        assert len(bus._interceptors.get(EventType.TOOL_START, [])) == 1
        priority, handler = bus._interceptors[EventType.TOOL_START][0]
        assert priority == 5
        assert handler is not None

    def test_load_unknown_event_type(self):
        """测试未知事件类型被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "unknown_event": [
                    {"type": "script", "path": "./test.sh"}
                ]
            }
        }
        load_hooks_from_config(config, bus)
        # 无拦截器注册
        assert len(bus._interceptors) == 0

    def test_load_invalid_handler_type(self):
        """测试无效 handler 类型被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "tool_start": [
                    {"type": "invalid_type", "path": "./test.sh"}
                ]
            }
        }
        load_hooks_from_config(config, bus)
        assert len(bus._interceptors) == 0

    def test_load_missing_script_path(self):
        """测试缺少 path 的脚本配置被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "tool_start": [
                    {"type": "script"}
                ]
            }
        }
        load_hooks_from_config(config, bus)
        assert len(bus._interceptors) == 0

    def test_load_missing_python_module(self):
        """测试缺少 module 的 Python 配置被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "tool_start": [
                    {"type": "python", "function": "test"}
                ]
            }
        }
        load_hooks_from_config(config, bus)
        assert len(bus._interceptors) == 0

    def test_load_nonexistent_python_module(self):
        """测试不存在的 Python 模块被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "tool_start": [
                    {"type": "python", "module": "nonexistent_module", "function": "test"}
                ]
            }
        }
        load_hooks_from_config(config, bus)
        assert len(bus._interceptors) == 0

    def test_load_hooks_not_list(self):
        """测试 hooks 值不是列表时被跳过。"""
        bus = EventBus()
        config = {
            "hooks": {
                "tool_start": "not_a_list"
            }
        }
        load_hooks_from_config(config, bus)
        assert len(bus._interceptors) == 0


class TestCreateHandler:
    """测试 _create_handler 函数。"""

    def test_create_script_handler(self):
        """测试创建 ScriptHook handler。"""
        handler = _create_handler({"type": "script", "path": "./test.sh", "timeout": 10})
        assert isinstance(handler, ScriptHook)
        assert handler.timeout == 10

    def test_create_python_handler(self):
        """测试创建 Python handler。"""
        handler = _create_handler({
            "type": "python",
            "module": "src.hooks.dangerous_command_guard",
            "function": "dangerous_command_guard",
        })
        assert handler is not None
        assert callable(handler)

    def test_create_handler_missing_type(self):
        """测试缺少 type 返回 None。"""
        handler = _create_handler({"path": "./test.sh"})
        assert handler is None

    def test_create_handler_invalid_type(self):
        """测试无效 type 返回 None。"""
        handler = _create_handler({"type": "invalid"})
        assert handler is None
