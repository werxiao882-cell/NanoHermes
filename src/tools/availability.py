"""工具可用性检查。

每个工具可以提供一个 check_fn 函数，用于判断该工具当前是否可用。
典型检查项：
- API Key 是否存在
- 服务是否正在运行
- 二进制文件是否已安装

优化：
- 检查结果按调用缓存，避免重复检查
- 相同 check_fn 去重，多次工具共享同一检查函数只执行一次
- 异常视为不可用（fail-safe）
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# 缓存：check_fn 的 id → 检查结果
_check_cache: dict[int, bool] = {}


def check_tool_availability(check_fn) -> bool:
    """检查工具是否可用。

    检查逻辑：
    1. 先查缓存（相同 check_fn 只执行一次）
    2. 执行 check_fn
    3. 缓存结果
    4. 异常视为不可用

    Args:
        check_fn: 可用性检查函数，返回 True/False。

    Returns:
        True 表示工具可用，False 表示不可用。
    """
    if check_fn is None:
        return True  # 没有检查函数，默认可用

    # 使用函数对象的 id 作为缓存键
    cache_key = id(check_fn)
    if cache_key in _check_cache:
        return _check_cache[cache_key]

    try:
        result = bool(check_fn())
        _check_cache[cache_key] = result
        return result
    except Exception as e:
        # 异常视为不可用
        logger.warning(f"工具可用性检查失败: {e}")
        _check_cache[cache_key] = False
        return False


def clear_check_cache() -> None:
    """清除可用性检查缓存。仅用于测试。"""
    _check_cache.clear()
