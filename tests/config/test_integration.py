"""配置系统集成测试。

测试完整配置加载流程，包括与 provider 注册表的集成。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest


class TestFullConfigLoad:
    """完整配置加载测试。"""

    def test_load_with_all_sources(self):
        """测试从所有来源加载配置。"""
        from src.config import load_config, Config
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建全局配置
            global_path = Path(tmpdir) / "global.json"
            global_path.write_text(json.dumps({
                "tui": {"typing_speed": 15},
            }))
            
            # 创建项目配置
            project_path = Path(tmpdir) / "project.json"
            project_path.write_text(json.dumps({
                "model": {"provider": "openai", "name": "gpt-4o"},
                "tui": {"typing_speed": 20},  # 覆盖全局
            }))
            
            with mock.patch.dict(os.environ, {
                "OPENAI_API_KEY": "sk-test",
                "DASHSCOPE_API_KEY": "ds-test",
            }, clear=True):
                with mock.patch.object(Path, "home", return_value=Path(tmpdir)):
                    config = load_config(config_file=str(project_path))
                    
                    # 项目配置覆盖全局
                    assert config.model.provider == "openai"
                    assert config.model.name == "gpt-4o"
                    assert config.tui.typing_speed == 20
                    
                    # 环境变量提供商已加载
                    assert "openai" in config.providers
                    assert config.providers["openai"].api_key_env == "OPENAI_API_KEY"

    def test_config_roundtrip(self):
        """测试配置序列化往返。"""
        from src.config import Config
        
        original = Config(
            model={"provider": "openai", "name": "gpt-4o", "context_length": 128000},
            providers={
                "openai": {"base_url": "https://api.openai.com/v1", "api_key_env": "OPENAI_API_KEY"},
            },
            tui={"typing_speed": 25, "show_tool_panel": False},
            auxiliary={"provider": "openai", "model": "gpt-4o-mini", "max_tokens": 2000},
        )
        
        # 序列化
        d = original.to_dict()
        
        # 反序列化
        restored = Config.from_dict(d)
        
        assert restored.model.provider == original.model.provider
        assert restored.model.name == original.model.name
        assert restored.model.context_length == original.model.context_length
        assert restored.tui.typing_speed == original.tui.typing_speed
        assert restored.auxiliary.max_tokens == original.auxiliary.max_tokens


class TestProviderRegistryIntegration:
    """Provider 注册表集成测试。"""

    def test_base_url_from_registry(self):
        """测试从注册表获取 base_url 默认值。"""
        from src.config import load_config, get_base_url
        
        # 导入 builtins 以注册提供商
        import src.provider.builtins
        
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            with mock.patch("src.config.loader.load_dotenv"):
                config = load_config(provider="openai")
                url = get_base_url(config)
                
                # 应从注册表获取 OpenAI 默认 URL
                assert url == "https://api.openai.com/v1"

    def test_anthropic_base_url_none(self):
        """测试 Anthropic base_url 为 None（使用 SDK 默认）。"""
        from src.config import load_config, get_base_url
        
        import src.provider.builtins
        
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}, clear=True):
            with mock.patch("src.config.loader.load_dotenv"):
                config = load_config(provider="anthropic")
                url = get_base_url(config)
                
                # Anthropic 无 base_url，返回 None
                assert url is None


class TestMcpConfig:
    """MCP 配置测试。"""

    def test_mcp_servers_config(self):
        """测试 MCP 服务器配置。"""
        from src.config import Config
        
        config = Config(
            mcp={
                "servers": [
                    {
                        "name": "filesystem",
                        "transport": "stdio",
                        "command": "mcp-server-filesystem",
                        "args": ["--root", "/home"],
                    },
                    {
                        "name": "http-server",
                        "transport": "streamable_http",
                        "url": "http://localhost:8000/mcp",
                    },
                ],
            },
        )
        
        assert len(config.mcp.servers) == 2
        assert config.mcp.servers[0].name == "filesystem"
        assert config.mcp.servers[0].transport == "stdio"
        assert config.mcp.servers[1].url == "http://localhost:8000/mcp"


class TestConfigValidationErrors:
    """配置验证错误测试。"""

    def test_invalid_transport_error(self):
        """测试无效传输类型错误。"""
        from src.config import Config
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Config(
                mcp={
                    "servers": [
                        {"name": "test", "transport": "invalid_type"},
                    ],
                },
            )
        
        assert "transport 必须是" in str(exc_info.value)

    def test_invalid_position_error(self):
        """测试无效面板位置错误。"""
        from src.config import Config
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Config(
                tui={"tool_panel_position": "invalid"},
            )
        
        assert "tool_panel_position 必须是" in str(exc_info.value)