"""配置数据模型验证测试。

测试 src/config/models.py 中的 Pydantic 模型验证逻辑。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


class TestModelConfig:
    """ModelConfig 数据模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import ModelConfig
        config = ModelConfig()
        assert config.provider == "dashscope"
        assert config.name == "qwen3.6-plus"
        assert config.context_length is None

    def test_custom_values(self):
        """测试自定义值。"""
        from src.config.models import ModelConfig
        config = ModelConfig(
            provider="openai",
            name="gpt-4o",
            context_length=128000,
        )
        assert config.provider == "openai"
        assert config.name == "gpt-4o"
        assert config.context_length == 128000

    def test_from_dict(self):
        """测试从字典创建。"""
        from src.config.models import ModelConfig
        config = ModelConfig.model_validate({
            "provider": "anthropic",
            "name": "claude-sonnet-4",
        })
        assert config.provider == "anthropic"
        assert config.name == "claude-sonnet-4"


class TestProviderConfig:
    """ProviderConfig 数据模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import ProviderConfig
        config = ProviderConfig()
        assert config.base_url is None
        assert config.api_key_env == ""

    def test_custom_values(self):
        """测试自定义值。"""
        from src.config.models import ProviderConfig
        config = ProviderConfig(
            base_url="https://api.openai.com/v1",
            api_key_env="OPENAI_API_KEY",
        )
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key_env == "OPENAI_API_KEY"


class TestMcpServerConfig:
    """McpServerConfig 数据模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import McpServerConfig
        config = McpServerConfig(name="test-server")
        assert config.name == "test-server"
        assert config.transport == "stdio"
        assert config.command is None
        assert config.args == []
        assert config.url is None
        assert config.headers == {}

    def test_valid_transports(self):
        """测试有效的传输类型。"""
        from src.config.models import McpServerConfig
        for transport in ["stdio", "streamable_http", "http_sse"]:
            config = McpServerConfig(name="test", transport=transport)
            assert config.transport == transport

    def test_invalid_transport(self):
        """测试无效的传输类型。"""
        from src.config.models import McpServerConfig
        with pytest.raises(ValidationError) as exc_info:
            McpServerConfig(name="test", transport="invalid")
        assert "transport 必须是" in str(exc_info.value)

    def test_http_config(self):
        """测试 HTTP 配置。"""
        from src.config.models import McpServerConfig
        config = McpServerConfig(
            name="http-server",
            transport="streamable_http",
            url="http://localhost:8000/mcp",
            headers={"Authorization": "Bearer token"},
        )
        assert config.url == "http://localhost:8000/mcp"
        assert config.headers == {"Authorization": "Bearer token"}


class TestTuiConfig:
    """TuiConfig 数据模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import TuiConfig
        config = TuiConfig()
        assert config.typing_speed == 10
        assert config.show_tool_panel is True
        assert config.tool_panel_position == "right"

    def test_valid_positions(self):
        """测试有效的面板位置。"""
        from src.config.models import TuiConfig
        for position in ["left", "right", "bottom"]:
            config = TuiConfig(tool_panel_position=position)
            assert config.tool_panel_position == position

    def test_invalid_position(self):
        """测试无效的面板位置。"""
        from src.config.models import TuiConfig
        with pytest.raises(ValidationError) as exc_info:
            TuiConfig(tool_panel_position="top")
        assert "tool_panel_position 必须是" in str(exc_info.value)


class TestAuxiliaryConfig:
    """AuxiliaryConfig 数据模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import AuxiliaryConfig
        config = AuxiliaryConfig()
        assert config.provider == "main"
        assert config.model == ""
        assert config.max_tokens is None
        assert config.temperature is None

    def test_custom_values(self):
        """测试自定义值。"""
        from src.config.models import AuxiliaryConfig
        config = AuxiliaryConfig(
            provider="openai",
            model="gpt-4o-mini",
            max_tokens=2000,
            temperature=0.3,
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o-mini"
        assert config.max_tokens == 2000
        assert config.temperature == 0.3


class TestConfig:
    """Config 根模型测试。"""

    def test_default_values(self):
        """测试默认值。"""
        from src.config.models import Config
        config = Config()
        assert config.model.provider == "dashscope"
        assert config.providers == {}
        assert config.mcp.servers == []
        assert config.tui.typing_speed == 10
        assert config.auxiliary.provider == "main"

    def test_from_dict_full(self):
        """测试从完整字典创建。"""
        from src.config.models import Config
        config = Config.from_dict({
            "model": {
                "provider": "openai",
                "name": "gpt-4o",
            },
            "providers": {
                "openai": {
                    "base_url": "https://api.openai.com/v1",
                    "api_key_env": "OPENAI_API_KEY",
                },
            },
            "tui": {
                "typing_speed": 20,
                "show_tool_panel": False,
            },
        })
        assert config.model.provider == "openai"
        assert config.model.name == "gpt-4o"
        assert config.providers["openai"].base_url == "https://api.openai.com/v1"
        assert config.tui.typing_speed == 20
        assert config.tui.show_tool_panel is False

    def test_from_dict_ignore_unknown(self):
        """测试忽略未知字段。"""
        from src.config.models import Config
        config = Config.from_dict({
            "model": {"provider": "openai"},
            "unknown_field": "should be ignored",
        })
        assert config.model.provider == "openai"

    def test_to_dict(self):
        """测试转换为字典。"""
        from src.config.models import Config
        config = Config(
            model={"provider": "openai", "name": "gpt-4o"},
        )
        d = config.to_dict()
        assert d["model"]["provider"] == "openai"
        assert d["model"]["name"] == "gpt-4o"
        # 不包含 None 值
        assert "context_length" not in d["model"]