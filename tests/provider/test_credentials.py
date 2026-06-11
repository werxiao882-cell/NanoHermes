"""测试: 凭证解析链。"""

import os
import pytest

from src.provider.credentials import (
    resolve_credentials,
    resolve_base_url,
    CredentialResult,
)


class TestResolveCredentials:
    """测试 resolve_credentials 函数。"""

    def test_explicit_key_has_highest_priority(self):
        """测试显式 Key 具有最高优先级。"""
        os.environ["TEST_API_KEY"] = "env-key-value"
        try:
            result = resolve_credentials(
                env_vars=["TEST_API_KEY"],
                explicit_key="explicit-key",
            )
            assert result.api_key == "explicit-key"
            assert result.source == "explicit"
        finally:
            del os.environ["TEST_API_KEY"]

    def test_resolve_from_env_var(self):
        """测试从环境变量解析凭证。"""
        os.environ["MY_API_KEY"] = "secret-key-123"
        try:
            result = resolve_credentials(env_vars=["MY_API_KEY"])
            assert result.api_key == "secret-key-123"
            assert result.source == "env"
        finally:
            del os.environ["MY_API_KEY"]

    def test_env_var_priority_order(self):
        """测试环境变量优先级顺序。"""
        os.environ["PRIMARY_KEY"] = "primary-value"
        os.environ["SECONDARY_KEY"] = "secondary-value"
        try:
            result = resolve_credentials(env_vars=["PRIMARY_KEY", "SECONDARY_KEY"])
            assert result.api_key == "primary-value"  # 第一个非空值
        finally:
            del os.environ["PRIMARY_KEY"]
            del os.environ["SECONDARY_KEY"]

    def test_fallback_to_secondary_env_var(self):
        """测试回退到次要环境变量。"""
        os.environ["SECONDARY_KEY"] = "secondary-value"
        try:
            result = resolve_credentials(env_vars=["MISSING_KEY", "SECONDARY_KEY"])
            assert result.api_key == "secondary-value"
        finally:
            del os.environ["SECONDARY_KEY"]

    def test_raises_when_no_key_found(self):
        """测试所有来源都没有 Key 时抛出 ValueError。"""
        with pytest.raises(ValueError, match="未找到 API Key"):
            resolve_credentials(env_vars=["NONEXISTENT_KEY_1", "NONEXISTENT_KEY_2"])

    def test_base_url_passed_through(self):
        """测试 base_url 正确传递到结果中。"""
        os.environ["TEST_KEY"] = "key"
        try:
            result = resolve_credentials(
                env_vars=["TEST_KEY"],
                base_url="https://custom.example.com/v1",
            )
            assert result.base_url == "https://custom.example.com/v1"
        finally:
            del os.environ["TEST_KEY"]


class TestResolveBaseUrl:
    """测试 resolve_base_url 函数。"""

    def test_config_url_has_highest_priority(self):
        """测试配置 URL 具有最高优先级。"""
        result = resolve_base_url(
            config_url="https://config.example.com",
            profile_url="https://profile.example.com",
            env_var="BASE_URL",
        )
        assert result == "https://config.example.com"

    def test_profile_url_when_no_config(self):
        """测试无配置时使用 Profile URL。"""
        result = resolve_base_url(
            config_url=None,
            profile_url="https://profile.example.com",
        )
        assert result == "https://profile.example.com"

    def test_env_var_as_last_resort(self):
        """测试环境变量作为最后手段。"""
        os.environ["MY_BASE_URL"] = "https://env.example.com"
        try:
            result = resolve_base_url(
                config_url=None,
                profile_url=None,
                env_var="MY_BASE_URL",
            )
            assert result == "https://env.example.com"
        finally:
            del os.environ["MY_BASE_URL"]

    def test_returns_none_when_all_empty(self):
        """测试所有来源都为空时返回 None。"""
        result = resolve_base_url()
        assert result is None


class TestKeyIsolation:
    """测试 API Key 隔离（防泄露检查）。"""

    def test_openrouter_key_not_sent_to_custom_endpoint(self):
        """测试 OpenRouter Key 不发送到自定义端点。"""
        os.environ["OPENROUTER_API_KEY"] = "or-secret"
        os.environ["CUSTOM_API_KEY"] = "custom-secret"
        try:
            # 自定义端点不应该使用 OPENROUTER_API_KEY
            result = resolve_credentials(
                env_vars=["OPENROUTER_API_KEY", "CUSTOM_API_KEY"],
                base_url="https://my-custom-server.com/v1",
            )
            # 应该使用 CUSTOM_API_KEY 而非 OPENROUTER_API_KEY
            assert result.api_key == "custom-secret"
        finally:
            del os.environ["OPENROUTER_API_KEY"]
            del os.environ["CUSTOM_API_KEY"]

    def test_openrouter_key_ok_for_openrouter_url(self):
        """测试 OpenRouter Key 可以用于 OpenRouter 端点。"""
        os.environ["OPENROUTER_API_KEY"] = "or-secret"
        try:
            result = resolve_credentials(
                env_vars=["OPENROUTER_API_KEY"],
                base_url="https://openrouter.ai/api/v1",
            )
            assert result.api_key == "or-secret"
        finally:
            del os.environ["OPENROUTER_API_KEY"]
