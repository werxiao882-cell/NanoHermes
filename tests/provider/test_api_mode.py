"""测试: API Mode 路由。"""

import pytest

from src.provider.api_mode import ApiMode, resolve_api_mode, get_client_type
from src.provider.profile import ProviderProfile


class TestResolveApiMode:
    """测试 resolve_api_mode 函数。"""

    def test_explicit_mode_has_highest_priority(self):
        """测试显式模式具有最高优先级。"""
        result = resolve_api_mode(explicit_mode="anthropic_messages")
        assert result == ApiMode.ANTHROPIC_MESSAGES

    def test_invalid_explicit_mode_raises(self):
        """测试无效的显式模式抛出 ValueError。"""
        with pytest.raises(ValueError, match="不支持的 api_mode"):
            resolve_api_mode(explicit_mode="invalid_mode")

    def test_profile_mode_as_second_priority(self):
        """测试 Profile 模式作为第二优先级。"""
        profile = ProviderProfile(
            id="anthropic",
            name="Anthropic",
            api_mode="anthropic_messages",
        )
        result = resolve_api_mode(profile=profile)
        assert result == ApiMode.ANTHROPIC_MESSAGES

    def test_base_url_heuristic_anthropic(self):
        """测试 base_url 启发式检测 Anthropic。"""
        result = resolve_api_mode(base_url="https://api.anthropic.com/v1")
        assert result == ApiMode.ANTHROPIC_MESSAGES

    def test_base_url_heuristic_codex(self):
        """测试 base_url 启发式检测 Codex。"""
        result = resolve_api_mode(base_url="https://api.openai.com/codex")
        assert result == ApiMode.CODEX_RESPONSES

    def test_default_to_chat_completions(self):
        """测试默认值为 chat_completions。"""
        result = resolve_api_mode()
        assert result == ApiMode.CHAT_COMPLETIONS

    def test_explicit_overrides_profile(self):
        """测试显式模式覆盖 Profile 模式。"""
        profile = ProviderProfile(
            id="test",
            name="Test",
            api_mode="anthropic_messages",
        )
        result = resolve_api_mode(explicit_mode="chat_completions", profile=profile)
        assert result == ApiMode.CHAT_COMPLETIONS

    def test_profile_overrides_heuristic(self):
        """测试 Profile 模式覆盖启发式检测。"""
        profile = ProviderProfile(
            id="test",
            name="Test",
            api_mode="chat_completions",
        )
        # base_url 指向 Anthropic，但 Profile 指定 chat_completions
        result = resolve_api_mode(
            profile=profile,
            base_url="https://api.anthropic.com",
        )
        assert result == ApiMode.CHAT_COMPLETIONS


class TestGetClientType:
    """测试 get_client_type 函数。"""

    def test_chat_completions_uses_openai(self):
        """测试 chat_completions 使用 OpenAI 客户端。"""
        assert get_client_type(ApiMode.CHAT_COMPLETIONS) == "openai"

    def test_anthropic_messages_uses_anthropic(self):
        """测试 anthropic_messages 使用 Anthropic 客户端。"""
        assert get_client_type(ApiMode.ANTHROPIC_MESSAGES) == "anthropic"

    def test_codex_responses_uses_openai(self):
        """测试 codex_responses 使用 OpenAI 客户端。"""
        assert get_client_type(ApiMode.CODEX_RESPONSES) == "openai"
