"""技能审查后台任务单元测试。"""

import time
import pytest
from unittest.mock import Mock
from src.background.skill_review import (
    skill_review_handler,
    skill_review_trigger,
    register_skill_review_task,
    reset_last_review_time,
    SKILL_REVIEW_MIN_TURNS,
    SKILL_REVIEW_MIN_INTERVAL_SECONDS,
)


@pytest.fixture(autouse=True)
def reset_time():
    """每个测试前重置上次审查时间。"""
    reset_last_review_time()
    yield
    reset_last_review_time()


class TestSkillReviewTrigger:
    """测试技能审查触发条件。"""

    def test_trigger_with_enough_iterations_and_time(self):
        """迭代数和时间间隔都满足时触发。"""
        event_data = {
            "messages": [{"role": "user", "content": f"msg {i}"} for i in range(20)],
            "iteration": SKILL_REVIEW_MIN_TURNS,
        }
        assert skill_review_trigger(event_data) is True

    def test_no_trigger_with_few_iterations(self):
        """迭代数不足时不触发。"""
        event_data = {
            "messages": [{"role": "user", "content": f"msg {i}"} for i in range(20)],
            "iteration": SKILL_REVIEW_MIN_TURNS - 1,
        }
        assert skill_review_trigger(event_data) is False

    def test_no_trigger_within_interval(self):
        """时间间隔不足时不触发。"""
        from src.background import skill_review
        skill_review._last_review_time = time.time()

        event_data = {
            "messages": [{"role": "user", "content": f"msg {i}"} for i in range(20)],
            "iteration": SKILL_REVIEW_MIN_TURNS,
        }
        assert skill_review_trigger(event_data) is False

    def test_trigger_after_interval(self):
        """时间间隔满足时触发。"""
        from src.background import skill_review
        skill_review._last_review_time = time.time() - SKILL_REVIEW_MIN_INTERVAL_SECONDS - 1

        event_data = {
            "messages": [{"role": "user", "content": f"msg {i}"} for i in range(20)],
            "iteration": SKILL_REVIEW_MIN_TURNS,
        }
        assert skill_review_trigger(event_data) is True


class TestSkillReviewHandler:
    """测试技能审查处理器。"""

    def test_handler_returns_error_without_model_caller(self):
        """缺少 model_caller 时返回错误。"""
        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "tool_dispatch": Mock(),
        }

        result = skill_review_handler(event_data)
        assert result["reviewed"] is False
        assert result["error"] == "no_model_caller"

    def test_handler_returns_error_without_tool_dispatch(self):
        """缺少 tool_dispatch 时返回错误。"""
        event_data = {
            "messages": [{"role": "user", "content": "test"}],
            "model_caller": Mock(),
        }

        result = skill_review_handler(event_data)
        assert result["reviewed"] is False
        assert result["error"] == "no_tool_dispatch"


class TestRegisterSkillReviewTask:
    """测试注册技能审查任务。"""

    def test_register_task(self):
        """注册任务到调度器。"""
        mock_scheduler = Mock()
        mock_caller = Mock()
        mock_dispatch = Mock()

        register_skill_review_task(
            scheduler=mock_scheduler,
            model_caller=mock_caller,
            tool_dispatch=mock_dispatch,
        )

        mock_scheduler.register_task.assert_called_once()
        call_args = mock_scheduler.register_task.call_args
        assert call_args[1]["name"] == "skill_review"
        assert call_args[1]["enabled"] is True

    def test_register_disabled_task(self):
        """注册禁用的任务。"""
        mock_scheduler = Mock()

        register_skill_review_task(
            scheduler=mock_scheduler,
            model_caller=Mock(),
            tool_dispatch=Mock(),
            enabled=False,
        )

        call_args = mock_scheduler.register_task.call_args
        assert call_args[1]["enabled"] is False

    def test_handler_injects_dependencies(self):
        """处理器注入依赖到 event_data。"""
        mock_scheduler = Mock()
        mock_caller = Mock()
        mock_dispatch = Mock()
        mock_schemas = [{"name": "skill_manage"}]

        register_skill_review_task(
            scheduler=mock_scheduler,
            model_caller=mock_caller,
            tool_dispatch=mock_dispatch,
            tool_schemas=mock_schemas,
        )

        # 获取注册的处理器
        handler = mock_scheduler.register_task.call_args[1]["handler"]

        # 调用处理器（会失败因为没有真正的 fork_agent，但依赖会被注入）
        event_data = {"messages": [{"role": "user", "content": "test"}]}
        try:
            handler(event_data)
        except Exception:
            pass

        # 验证依赖被注入
        assert event_data["model_caller"] is mock_caller
        assert event_data["tool_dispatch"] is mock_dispatch
        assert event_data["tool_schemas"] is mock_schemas
