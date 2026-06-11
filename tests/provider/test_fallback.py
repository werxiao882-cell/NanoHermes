"""测试: 回退模型链。"""

import pytest

from src.provider.fallback import FallbackChain, FallbackEntry


class TestFallbackChain:
    """测试 FallbackChain 类。"""

    def test_has_no_fallbacks_when_empty(self):
        """测试空回退链返回 has_fallbacks=False。"""
        chain = FallbackChain()
        assert chain.has_fallbacks is False

    def test_has_fallbacks_when_configured(self):
        """测试配置回退后返回 has_fallbacks=True。"""
        chain = FallbackChain(entries=[
            FallbackEntry(provider="openai", model="gpt-4o"),
        ])
        assert chain.has_fallbacks is True

    def test_get_next_returns_first_entry(self):
        """测试 get_next 返回第一个回退条目。"""
        entry = FallbackEntry(provider="openai", model="gpt-4o")
        chain = FallbackChain(entries=[entry])

        result = chain.get_next(0)
        assert result is not None
        assert result.provider == "openai"
        assert result.model == "gpt-4o"

    def test_get_next_returns_none_after_activation(self):
        """测试激活后 get_next 返回 None（一次性语义）。"""
        entry = FallbackEntry(provider="openai", model="gpt-4o")
        chain = FallbackChain(entries=[entry])
        chain.activate(entry)

        assert chain.get_next(0) is None

    def test_activate_sets_flag(self):
        """测试激活设置 is_activated 标志。"""
        entry = FallbackEntry(provider="openai", model="gpt-4o")
        chain = FallbackChain(entries=[entry])

        assert chain.is_activated is False
        chain.activate(entry)
        assert chain.is_activated is True

    def test_active_fallback_returns_entry(self):
        """测试 active_fallback 返回已激活的条目。"""
        entry = FallbackEntry(provider="anthropic", model="claude-sonnet-4")
        chain = FallbackChain(entries=[entry])
        chain.activate(entry)

        assert chain.active_fallback == entry

    def test_reset_clears_activation(self):
        """测试重置清除激活状态。"""
        entry = FallbackEntry(provider="openai", model="gpt-4o")
        chain = FallbackChain(entries=[entry])
        chain.activate(entry)

        chain.reset()
        assert chain.is_activated is False
        assert chain.active_fallback is None

    def test_multiple_fallbacks(self):
        """测试多个回退条目按顺序返回。"""
        entries = [
            FallbackEntry(provider="openai", model="gpt-4o"),
            FallbackEntry(provider="anthropic", model="claude-sonnet-4"),
            FallbackEntry(provider="openai", model="gpt-4o-mini"),
        ]
        chain = FallbackChain(entries=entries)

        assert chain.get_next(0).provider == "openai"  # type: ignore[union-attr]
        assert chain.get_next(1).provider == "anthropic"  # type: ignore[union-attr]
        assert chain.get_next(2).provider == "openai"  # type: ignore[union-attr]
        assert chain.get_next(3) is None  # 超出范围
