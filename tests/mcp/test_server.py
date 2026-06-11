"""MCP Server 集成测试"""

import pytest
from src.mcp.server import create_server, configure_logging
from src.mcp.transports import TransportMode, TransportConfig


class TestCreateServer:
    def test_default_name(self):
        mcp = create_server()
        assert mcp.name == "nanohermes-mcp"

    def test_custom_name(self):
        mcp = create_server(name="custom-server")
        assert mcp.name == "custom-server"


class TestConfigureLogging:
    def test_default_level(self, monkeypatch):
        monkeypatch.delenv("NANOHERMES_MCP_LOG_LEVEL", raising=False)
        level = configure_logging()
        assert level == 20 or level == 30  # WARNING or INFO

    def test_custom_level(self, monkeypatch):
        monkeypatch.setenv("NANOHERMES_MCP_LOG_LEVEL", "DEBUG")
        level = configure_logging()
        assert level == 10  # DEBUG


class TestTransportConfig:
    def test_stdio_default(self):
        config = TransportConfig.from_args()
        assert config.mode == TransportMode.STDIO

    def test_streamable_http(self):
        config = TransportConfig.from_args(transport="streamable-http", port=9000)
        assert config.mode == TransportMode.STREAMABLE_HTTP
        assert config.port == 9000

    def test_get_server_url_stdio(self):
        config = TransportConfig.from_args()
        with pytest.raises(ValueError):
            config.get_server_url()

    def test_get_server_url_http(self):
        config = TransportConfig.from_args(transport="streamable-http")
        url = config.get_server_url()
        assert "8000" in url
