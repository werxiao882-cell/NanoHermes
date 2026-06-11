"""测试: Provider Profile 和注册表。"""

import pytest

from src.provider.profile import (
    ProviderProfile,
    FallbackModel,
    ProviderRegistry,
    register_provider,
    get_provider_profile,
    list_providers,
    resolve_provider_alias,
)


@pytest.fixture(autouse=True)
def _clear_registry():
    """每个测试前后清空注册表，确保测试隔离。"""
    ProviderRegistry.clear()
    yield
    ProviderRegistry.clear()


class TestProviderProfile:
    """测试 ProviderProfile 数据结构。"""

    def test_create_minimal_profile(self):
        """测试创建最小配置文件（仅必填字段）。"""
        profile = ProviderProfile(id="test", name="Test", api_mode="chat_completions")
        assert profile.id == "test"
        assert profile.name == "Test"
        assert profile.api_mode == "chat_completions"
        assert profile.base_url is None
        assert profile.env_vars == []
        assert profile.fallback_models == []
        assert profile.aliases == []

    def test_create_full_profile(self):
        """测试创建完整配置文件（所有字段）。"""
        profile = ProviderProfile(
            id="openai",
            name="OpenAI",
            api_mode="chat_completions",
            base_url="https://api.openai.com/v1",
            env_vars=["OPENAI_API_KEY"],
            fallback_models=[FallbackModel(provider="openai", model="gpt-4o-mini")],
            aliases=["oai"],
        )
        assert profile.base_url == "https://api.openai.com/v1"
        assert profile.env_vars == ["OPENAI_API_KEY"]
        assert len(profile.fallback_models) == 1
        assert profile.fallback_models[0].model == "gpt-4o-mini"
        assert profile.aliases == ["oai"]


class TestProviderRegistry:
    """测试 ProviderRegistry 注册表。"""

    def test_register_and_get_profile(self):
        """测试注册和获取配置文件。"""
        profile = ProviderProfile(id="test", name="Test", api_mode="chat_completions")
        register_provider(profile)

        result = get_provider_profile("test")
        assert result is not None
        assert result.id == "test"
        assert result.name == "Test"

    def test_get_nonexistent_profile(self):
        """测试获取不存在的配置文件返回 None。"""
        result = get_provider_profile("nonexistent")
        assert result is None

    def test_list_providers(self):
        """测试列出所有已注册的提供商。"""
        register_provider(ProviderProfile(id="a", name="A", api_mode="chat_completions"))
        register_provider(ProviderProfile(id="b", name="B", api_mode="chat_completions"))

        ids = list_providers()
        assert set(ids) == {"a", "b"}

    def test_register_overwrites_existing(self):
        """测试注册同名提供商时覆盖旧配置。"""
        register_provider(ProviderProfile(id="test", name="Old", api_mode="chat_completions"))
        register_provider(ProviderProfile(id="test", name="New", api_mode="anthropic_messages"))

        result = get_provider_profile("test")
        assert result is not None
        assert result.name == "New"
        assert result.api_mode == "anthropic_messages"

    def test_alias_resolution(self):
        """测试别名解析。"""
        profile = ProviderProfile(
            id="openai",
            name="OpenAI",
            api_mode="chat_completions",
            aliases=["oai", "open"],
        )
        register_provider(profile)

        assert resolve_provider_alias("oai") == "openai"
        assert resolve_provider_alias("open") == "openai"
        assert resolve_provider_alias("unknown") is None

    def test_clear_registry(self):
        """测试清空注册表。"""
        register_provider(ProviderProfile(id="test", name="Test", api_mode="chat_completions"))
        ProviderRegistry.clear()

        assert list_providers() == []
        assert get_provider_profile("test") is None
