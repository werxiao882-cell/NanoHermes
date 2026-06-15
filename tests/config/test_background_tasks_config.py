"""后台任务配置系统单元测试。"""

import pytest
from src.config.models import (
    BackgroundTasksConfig,
    MemoryFlushConfig,
    SkillReviewConfig,
    Config,
)


class TestMemoryFlushConfig:
    """测试记忆刷写配置。"""

    def test_default_values(self):
        """测试默认值。"""
        config = MemoryFlushConfig()
        assert config.enabled is True
        assert config.min_messages == 10

    def test_custom_values(self):
        """测试自定义值。"""
        config = MemoryFlushConfig(enabled=False, min_messages=20)
        assert config.enabled is False
        assert config.min_messages == 20


class TestSkillReviewConfig:
    """测试技能审查配置。"""

    def test_default_values(self):
        """测试默认值。"""
        config = SkillReviewConfig()
        assert config.enabled is True
        assert config.min_turns == 10
        assert config.min_interval_minutes == 30
        assert config.curator_enabled is True

    def test_custom_values(self):
        """测试自定义值。"""
        config = SkillReviewConfig(
            enabled=False,
            min_turns=5,
            min_interval_minutes=60,
            curator_enabled=False,
        )
        assert config.enabled is False
        assert config.min_turns == 5
        assert config.min_interval_minutes == 60
        assert config.curator_enabled is False


class TestBackgroundTasksConfig:
    """测试后台任务配置。"""

    def test_default_values(self):
        """测试默认值。"""
        config = BackgroundTasksConfig()
        assert config.enabled is True
        assert config.max_concurrent == 2
        assert config.task_timeout_seconds == 300.0
        assert config.memory_flush.enabled is True
        assert config.skill_review.enabled is True

    def test_custom_values(self):
        """测试自定义值。"""
        config = BackgroundTasksConfig(
            enabled=False,
            max_concurrent=4,
            task_timeout_seconds=600.0,
            memory_flush=MemoryFlushConfig(enabled=False),
            skill_review=SkillReviewConfig(enabled=False),
        )
        assert config.enabled is False
        assert config.max_concurrent == 4
        assert config.task_timeout_seconds == 600.0
        assert config.memory_flush.enabled is False
        assert config.skill_review.enabled is False


class TestConfigWithBackgroundTasks:
    """测试根配置包含后台任务配置。"""

    def test_config_has_background_tasks(self):
        """测试 Config 包含 background_tasks 字段。"""
        config = Config()
        assert hasattr(config, "background_tasks")
        assert isinstance(config.background_tasks, BackgroundTasksConfig)

    def test_config_from_dict(self):
        """测试从字典创建配置。"""
        data = {
            "background_tasks": {
                "enabled": False,
                "max_concurrent": 3,
                "memory_flush": {
                    "enabled": False,
                    "min_messages": 15,
                },
                "skill_review": {
                    "enabled": False,
                    "min_turns": 5,
                },
            }
        }
        config = Config.from_dict(data)
        assert config.background_tasks.enabled is False
        assert config.background_tasks.max_concurrent == 3
        assert config.background_tasks.memory_flush.enabled is False
        assert config.background_tasks.memory_flush.min_messages == 15
        assert config.background_tasks.skill_review.enabled is False
        assert config.background_tasks.skill_review.min_turns == 5

    def test_config_to_dict(self):
        """测试配置转换为字典。"""
        config = Config()
        data = config.to_dict()
        assert "background_tasks" in data
        assert data["background_tasks"]["enabled"] is True
        assert data["background_tasks"]["max_concurrent"] == 2
