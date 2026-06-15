"""记忆刷写后台任务单元测试。"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.background.memory_flush import (
    memory_flush_handler,
    memory_flush_trigger,
    register_memory_flush_task,
    MEMORY_FLUSH_MIN_MESSAGES,
)


class TestMemoryFlushTrigger:
    """测试记忆刷写触发条件。"""

    def test_trigger_with_enough_messages(self):
        """消息数达到阈值时触发。"""
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(MEMORY_FLUSH_MIN_MESSAGES)]
        event_data = {"messages": messages}
        assert memory_flush_trigger(event_data) is True

    def test_no_trigger_with_few_messages(self):
        """消息数不足时不触发。"""
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(MEMORY_FLUSH_MIN_MESSAGES - 1)]
        event_data = {"messages": messages}
        assert memory_flush_trigger(event_data) is False

    def test_no_trigger_with_empty_messages(self):
        """空消息列表时不触发。"""
        event_data = {"messages": []}
        assert memory_flush_trigger(event_data) is False

    def test_no_trigger_with_missing_messages(self):
        """缺少 messages 字段时不触发。"""
        event_data = {}
        assert memory_flush_trigger(event_data) is False


class TestMemoryFlushHandler:
    """测试记忆刷写处理器。"""

    def test_handler_calls_run_background_review(self):
        """处理器调用 run_background_review。"""
        mock_provider = Mock()
        mock_caller = Mock()

        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "memory_provider": mock_provider,
            "model_caller": mock_caller,
        }

        with patch("src.background.review.run_background_review") as mock_review:
            mock_review.return_value = {
                "iterations": 2,
                "final_response": "saved",
                "elapsed": 1.0,
            }
            result = memory_flush_handler(event_data)

            mock_review.assert_called_once()
            assert result["extracted"] == 2
            assert result["response"] == "saved"

    def test_handler_returns_error_without_provider(self):
        """缺少 memory_provider 时返回错误。"""
        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "model_caller": Mock(),
        }

        result = memory_flush_handler(event_data)
        assert result["extracted"] == 0
        assert result["error"] == "no_memory_provider"

    def test_handler_returns_error_without_model_caller(self):
        """缺少 model_caller 时返回错误。"""
        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "memory_provider": Mock(),
        }

        result = memory_flush_handler(event_data)
        assert result["extracted"] == 0
        assert result["error"] == "no_model_caller"

    def test_handler_creates_memory_dispatch(self):
        """处理器创建自定义 memory_dispatch 路由到 provider。"""
        mock_provider = Mock()
        mock_provider.handle_tool_call.return_value = '{"success": true}'
        mock_caller = Mock()

        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "memory_provider": mock_provider,
            "model_caller": mock_caller,
        }

        with patch("src.background.review.run_background_review") as mock_review:
            mock_review.return_value = {"iterations": 1, "final_response": "", "elapsed": 0.5}
            memory_flush_handler(event_data)

            # 验证 run_background_review 被调用且传入了 tool_dispatch_override
            call_kwargs = mock_review.call_args[1]
            assert "tool_dispatch_override" in call_kwargs
            override = call_kwargs["tool_dispatch_override"]

            # 验证 override 路由 memory 工具到 provider
            override("memory", {"action": "add"})
            mock_provider.handle_tool_call.assert_called_once_with("memory", {"action": "add"})


class TestRegisterMemoryFlushTask:
    """测试注册记忆刷写任务。"""

    def test_register_task(self):
        """注册任务到调度器。"""
        mock_scheduler = Mock()
        mock_provider = Mock()
        mock_caller = Mock()
        mock_dispatch = Mock()

        register_memory_flush_task(
            scheduler=mock_scheduler,
            memory_provider=mock_provider,
            model_caller=mock_caller,
            tool_dispatch=mock_dispatch,
        )

        mock_scheduler.register_task.assert_called_once()
        call_args = mock_scheduler.register_task.call_args
        assert call_args[1]["name"] == "memory_flush"
        assert call_args[1]["enabled"] is True

    def test_register_disabled_task(self):
        """注册禁用的任务。"""
        mock_scheduler = Mock()

        register_memory_flush_task(
            scheduler=mock_scheduler,
            memory_provider=Mock(),
            model_caller=Mock(),
            tool_dispatch=Mock(),
            enabled=False,
        )

        call_args = mock_scheduler.register_task.call_args
        assert call_args[1]["enabled"] is False

    def test_handler_injects_dependencies(self):
        """处理器注入依赖到 event_data。"""
        mock_scheduler = Mock()
        mock_provider = Mock()
        mock_caller = Mock()
        mock_dispatch = Mock()
        mock_schemas = [{"name": "memory"}]

        register_memory_flush_task(
            scheduler=mock_scheduler,
            memory_provider=mock_provider,
            model_caller=mock_caller,
            tool_dispatch=mock_dispatch,
            tool_schemas=mock_schemas,
        )

        # 获取注册的处理器
        handler = mock_scheduler.register_task.call_args[1]["handler"]

        # 调用处理器（mock run_background_review）
        with patch("src.background.review.run_background_review") as mock_review:
            mock_review.return_value = {
                "iterations": 1,
                "final_response": "ok",
                "elapsed": 0.5,
            }

            event_data = {"messages": [{"role": "user", "content": "test"}]}
            result = handler(event_data)

            # 验证依赖被注入
            assert event_data["memory_provider"] is mock_provider
            assert event_data["model_caller"] is mock_caller
            assert event_data["tool_dispatch"] is mock_dispatch
            assert event_data["tool_schemas"] is mock_schemas

            # 验证结果
            assert result["extracted"] == 1
            assert result["response"] == "ok"
