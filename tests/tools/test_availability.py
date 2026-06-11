"""测试: 工具可用性检查。"""

import pytest

from src.tools.core.availability import check_tool_availability, clear_check_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """每个测试前后清空缓存。"""
    clear_check_cache()
    yield
    clear_check_cache()


class TestCheckToolAvailability:
    """测试 check_tool_availability 函数。"""

    def test_none_check_fn_returns_true(self):
        """测试 None check_fn 返回 True。"""
        assert check_tool_availability(None) is True

    def test_check_fn_returns_true(self):
        """测试 check_fn 返回 True。"""
        assert check_tool_availability(lambda: True) is True

    def test_check_fn_returns_false(self):
        """测试 check_fn 返回 False。"""
        assert check_tool_availability(lambda: False) is False

    def test_exception_returns_false(self):
        """测试 check_fn 抛出异常返回 False。"""
        def failing():
            raise ValueError("test error")
        assert check_tool_availability(failing) is False

    def test_cache_prevents_repeated_calls(self):
        """测试缓存防止重复调用。"""
        call_count = 0

        def counting():
            nonlocal call_count
            call_count += 1
            return True

        check_tool_availability(counting)
        check_tool_availability(counting)
        check_tool_availability(counting)

        # 由于使用 id 作为缓存键，每次调用都是同一个函数对象
        # 所以只执行一次
        assert call_count == 1
