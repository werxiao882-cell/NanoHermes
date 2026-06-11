"""客户端工具单元测试"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.mcp.client import McpClientManager, McpServiceConfig, load_service_config


class TestMcpServiceConfig:
    def test_default_values(self):
        config = McpServiceConfig(name="test", transport="stdio")
        assert config.is_active is True
        assert config.command is None

    def test_all_fields(self):
        config = McpServiceConfig(
            name="test",
            transport="streamable-http",
            url="http://localhost:8000/mcp",
        )
        assert config.url == "http://localhost:8000/mcp"


class TestLoadServiceConfig:
    def test_missing_file(self, tmp_path):
        config_path = tmp_path / "nonexistent.json"
        services = load_service_config(config_path)
        assert services == []

    def test_valid_config(self, tmp_path):
        config = {
            "mcpServers": {
                "test-service": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["test-mcp"],
                    "isActive": True,
                }
            }
        }
        config_path = tmp_path / "mcp_servers.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        services = load_service_config(config_path)
        assert len(services) == 1
        assert services[0].name == "test-service"

    def test_inactive_service(self, tmp_path):
        config = {
            "mcpServers": {
                "active-service": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["test"],
                    "isActive": True,
                },
                "inactive-service": {
                    "type": "stdio",
                    "command": "uvx",
                    "args": ["test"],
                    "isActive": False,
                }
            }
        }
        config_path = tmp_path / "mcp_servers.json"
        with open(config_path, "w") as f:
            json.dump(config, f)

        services = load_service_config(config_path)
        assert len(services) == 1
        assert services[0].name == "active-service"


class TestMcpClientManager:
    @pytest.mark.asyncio
    async def test_call_tool_not_connected(self):
        manager = McpClientManager()
        with pytest.raises(ConnectionError):
            await manager.call_tool("nonexistent", "tool")

    @pytest.mark.asyncio
    async def test_list_tools_empty(self):
        manager = McpClientManager()
        result = await manager.list_tools()
        assert result == {}
