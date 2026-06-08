"""Tests for auxiliary client module."""

import pytest
from unittest.mock import MagicMock, patch

from src.auxiliary.client import AuxiliaryClient
from src.config import AuxiliaryConfig


class TestAuxiliaryConfig:
    """Tests for AuxiliaryConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AuxiliaryConfig()
        assert config.provider == "main"
        assert config.model == ""
        assert config.max_tokens is None
        assert config.temperature is None

    def test_custom_config(self):
        """Test custom configuration values."""
        config = AuxiliaryConfig(
            provider="openai",
            model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.5,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5


class TestAuxiliaryClient:
    """Tests for AuxiliaryClient class."""

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        client = AuxiliaryClient()
        assert client._config.provider == "main"
        assert client._client is None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = AuxiliaryConfig(provider="openai", model="gpt-4o-mini")
        client = AuxiliaryClient(config=config)
        assert client._config.provider == "openai"
        assert client._config.model == "gpt-4o-mini"

    def test_init_with_main_credentials(self):
        """Test initialization with main conversation credentials."""
        from src.provider.credentials import CredentialResult
        from src.provider.api_mode import ApiMode

        creds = CredentialResult(
            api_key="test-key",
            base_url="https://test.com",
            source="env",
        )
        client = AuxiliaryClient(
            main_credentials=creds,
            main_api_mode=ApiMode.CHAT_COMPLETIONS,
        )
        assert client._main_credentials == creds
        assert client._main_api_mode == ApiMode.CHAT_COMPLETIONS

    def test_ensure_client_not_called_twice(self):
        """Test that _ensure_client doesn't recreate client."""
        client = AuxiliaryClient()
        client._client = MagicMock()
        # Should not raise or recreate
        client._ensure_client()
        assert client._client is not None

    def test_chat_completion_ensures_client(self):
        """Test that chat_completion calls _ensure_client."""
        client = AuxiliaryClient()
        client._ensure_client = MagicMock()
        client._client = MagicMock()
        client._client.chat_completion = MagicMock(return_value="response")

        client.chat_completion([{"role": "user", "content": "test"}])

        client._ensure_client.assert_called_once()

    def test_chat_completion_applies_max_tokens_default(self):
        """Test that chat_completion applies default max_tokens."""
        client = AuxiliaryClient()
        client._client = MagicMock()
        client._client.chat_completion = MagicMock(return_value="response")

        client.chat_completion([{"role": "user", "content": "test"}])

        # Should call with default max_tokens
        call_kwargs = client._client.chat_completion.call_args[1]
        assert "max_tokens" in call_kwargs
        assert call_kwargs["max_tokens"] == 4000  # Default value

    def test_chat_completion_uses_config_max_tokens(self):
        """Test that chat_completion uses config max_tokens if set."""
        config = AuxiliaryConfig(max_tokens=2000)
        client = AuxiliaryClient(config=config)
        client._client = MagicMock()
        client._client.chat_completion = MagicMock(return_value="response")

        client.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = client._client.chat_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 2000

    def test_chat_completion_overrides_max_tokens(self):
        """Test that explicit max_tokens overrides config."""
        config = AuxiliaryConfig(max_tokens=2000)
        client = AuxiliaryClient(config=config)
        client._client = MagicMock()
        client._client.chat_completion = MagicMock(return_value="response")

        client.chat_completion([{"role": "user", "content": "test"}], max_tokens=1000)

        call_kwargs = client._client.chat_completion.call_args[1]
        assert call_kwargs["max_tokens"] == 1000

    def test_chat_completion_passes_temperature(self):
        """Test that temperature is passed to client."""
        config = AuxiliaryConfig(temperature=0.7)
        client = AuxiliaryClient(config=config)
        client._client = MagicMock()
        client._client.chat_completion = MagicMock(return_value="response")

        client.chat_completion([{"role": "user", "content": "test"}])

        call_kwargs = client._client.chat_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.7

    def test_resolve_main_model_returns_default(self):
        """Test _resolve_main_model returns default model."""
        client = AuxiliaryClient()
        # Default implementation returns "gpt-4o"
        model = client._resolve_main_model()
        assert model == "gpt-4o"
