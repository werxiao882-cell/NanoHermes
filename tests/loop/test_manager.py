"""循环管理器测试。"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.loop import LoopConfig, LoopMode, LoopStatus, LoopState
from src.loop.manager import LoopManager


class TestLoopConfig:
    """测试循环配置。"""

    def test_default_config(self):
        config = LoopConfig()
        assert config.loop_id
        assert len(config.loop_id) == 8
        assert config.interval_seconds is None
        assert config.prompt is None
        assert config.mode == LoopMode.DYNAMIC

    def test_fixed_mode(self):
        config = LoopConfig(interval_seconds=300, mode=LoopMode.FIXED)
        assert config.interval_seconds == 300
        assert config.mode == LoopMode.FIXED
        assert not config.is_dynamic

    def test_dynamic_mode(self):
        config = LoopConfig(mode=LoopMode.DYNAMIC)
        assert config.is_dynamic

    def test_expiry(self):
        config = LoopConfig()
        expected = config.created_at + timedelta(days=7)
        assert abs((config.expires_at - expected).total_seconds()) < 1

    def test_is_expired(self):
        # 创建已过期的配置
        past = datetime.now(timezone.utc) - timedelta(days=8)
        config = LoopConfig(created_at=past)
        assert config.is_expired

    def test_not_expired(self):
        config = LoopConfig()
        assert not config.is_expired

    def test_serialization_roundtrip(self):
        config = LoopConfig(
            interval_seconds=300,
            prompt="测试提示",
            mode=LoopMode.FIXED,
        )
        data = config.to_meta_dict()
        restored = LoopConfig.from_meta_dict(data)

        assert restored.loop_id == config.loop_id
        assert restored.interval_seconds == config.interval_seconds
        assert restored.prompt == config.prompt
        assert restored.mode == config.mode


class TestLoopState:
    """测试循环状态。"""

    def test_default_state(self):
        config = LoopConfig()
        state = LoopState(config=config)
        assert state.status == LoopStatus.CREATED
        assert state.execution_count == 0
        assert state.last_error is None
        assert state.is_active

    def test_stopped_not_active(self):
        config = LoopConfig()
        state = LoopState(config=config, status=LoopStatus.STOPPED)
        assert not state.is_active

    def test_serialization(self):
        config = LoopConfig(interval_seconds=300, prompt="test")
        state = LoopState(config=config, execution_count=5)
        data = state.to_meta_dict()
        assert data["execution_count"] == 5
        assert data["status"] == "created"


class TestLoopManager:
    """测试循环管理器。"""

    def test_create_loop_fixed(self):
        manager = LoopManager()
        state = manager.create_loop(interval="5m", prompt="测试")

        assert state.config.mode == LoopMode.FIXED
        assert state.config.interval_seconds == 300
        assert state.config.prompt == "测试"
        assert state.status == LoopStatus.ACTIVE

    def test_create_loop_dynamic(self):
        manager = LoopManager()
        state = manager.create_loop(prompt="测试")

        assert state.config.is_dynamic
        assert state.config.prompt == "测试"

    def test_create_loop_maintenance(self):
        manager = LoopManager()
        state = manager.create_loop(interval="10m")

        assert state.config.mode == LoopMode.FIXED
        assert state.config.interval_seconds == 600
        assert state.config.prompt is not None

    def test_create_loop_bare(self):
        manager = LoopManager()
        state = manager.create_loop()

        assert state.config.is_dynamic
        assert state.config.prompt is not None

    def test_create_loop_replaces_existing(self):
        manager = LoopManager()
        state1 = manager.create_loop(prompt="第一个")
        state2 = manager.create_loop(prompt="第二个")

        assert manager.active_loop.loop_id == state2.config.loop_id
        assert state1.status == LoopStatus.STOPPED

    def test_stop_loop(self):
        manager = LoopManager()
        manager.create_loop(prompt="测试")
        state = manager.stop_loop()

        assert state is not None
        assert state.status == LoopStatus.STOPPED
        assert manager.active_loop is None

    def test_stop_no_active_loop(self):
        manager = LoopManager()
        state = manager.stop_loop()
        assert state is None

    def test_restore_expired_loop(self):
        manager = LoopManager()
        past = datetime.now(timezone.utc) - timedelta(days=8)
        config = LoopConfig(created_at=past)

        with pytest.raises(ValueError, match="过期"):
            manager.restore_loop(config)

    def test_restore_valid_loop(self):
        manager = LoopManager()
        config = LoopConfig(interval_seconds=300, prompt="恢复测试")
        state = manager.restore_loop(config)

        assert state.config.loop_id == config.loop_id
        assert state.status == LoopStatus.ACTIVE

    def test_invalid_interval(self):
        manager = LoopManager()
        with pytest.raises(ValueError, match="无法解析"):
            manager.create_loop(interval="invalid")


class TestLoopManagerExecution:
    """测试循环执行（异步）。"""

    @pytest.mark.asyncio
    async def test_single_execution_fixed(self):
        """测试固定间隔模式下单次执行。"""
        manager = LoopManager()
        state = manager.create_loop(interval="1m", prompt="测试提示")

        call_count = 0
        call_args = []

        async def mock_run(prompt):
            nonlocal call_count
            call_count += 1
            call_args.append(prompt)
            return {"final_response": "响应"}

        # 使用极短超时测试
        with patch.object(manager, "_extract_next_interval", return_value=0.01):
            task = asyncio.create_task(manager._run_loop(mock_run))
            await asyncio.sleep(0.05)
            manager.stop_loop()
            await asyncio.sleep(0.01)

        assert call_count >= 1
        assert call_args[0] == "测试提示"

    @pytest.mark.asyncio
    async def test_dynamic_interval_extraction(self):
        """测试动态间隔提取。"""
        manager = LoopManager()
        state = manager.create_loop(prompt="测试")

        # 测试提取方法
        interval = manager._extract_next_interval("完成检查 __next_interval: 5m__ 继续监控")
        assert interval == 300

    @pytest.mark.asyncio
    async def test_default_interval_when_no_marker(self):
        """测试无标记时使用默认间隔。"""
        manager = LoopManager()
        interval = manager._extract_next_interval("没有标记的响应")
        assert interval == 600  # DEFAULT_DYNAMIC_INTERVAL

    @pytest.mark.asyncio
    async def test_execution_error_continues(self):
        """测试执行出错时继续循环。"""
        manager = LoopManager()
        state = manager.create_loop(interval="1m", prompt="测试")

        call_count = 0

        async def mock_run_failing(prompt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("模拟错误")
            return {"final_response": "成功"}

        task = asyncio.create_task(manager._run_loop(mock_run_failing))
        await asyncio.sleep(0.05)
        manager.stop_loop()
        await asyncio.sleep(0.01)

        assert call_count >= 1
