"""配置数据模型。

使用 Pydantic 定义所有配置段，提供类型验证和默认值。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# 模型配置
# ============================================================================

class ModelConfig(BaseModel):
    """主模型配置。"""
    provider: str = "dashscope"
    name: str = "qwen3.6-plus"
    context_length: int | None = None


# ============================================================================
# 提供商配置
# ============================================================================

class ProviderConfig(BaseModel):
    """单个提供商配置。"""
    base_url: str | None = None
    api_key_env: str = ""


# ============================================================================
# MCP 配置
# ============================================================================

class McpServerConfig(BaseModel):
    """单个 MCP 服务器配置。"""
    name: str
    transport: str = "stdio"
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        valid = {"stdio", "streamable_http", "http_sse"}
        if v not in valid:
            raise ValueError(f"transport 必须是 {valid} 之一，得到: {v}")
        return v


class McpConfig(BaseModel):
    """MCP 配置段。"""
    servers: list[McpServerConfig] = Field(default_factory=list)


# ============================================================================
# TUI 配置
# ============================================================================

class TuiConfig(BaseModel):
    """TUI 配置段。"""
    typing_speed: int = 10
    show_tool_panel: bool = True
    tool_panel_position: str = "right"

    @field_validator("tool_panel_position")
    @classmethod
    def validate_position(cls, v: str) -> str:
        valid = {"left", "right", "bottom"}
        if v not in valid:
            raise ValueError(f"tool_panel_position 必须是 {valid} 之一，得到: {v}")
        return v


# ============================================================================
# 辅助 LLM 配置
# ============================================================================

class AuxiliaryConfig(BaseModel):
    """辅助 LLM 配置段。"""
    provider: str = "main"
    model: str = ""
    max_tokens: int | None = None
    temperature: float | None = None


# ============================================================================
# 根配置
# ============================================================================

class Config(BaseModel):
    """根配置对象，包含所有配置段。"""
    model: ModelConfig = Field(default_factory=ModelConfig)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    mcp: McpConfig = Field(default_factory=McpConfig)
    tui: TuiConfig = Field(default_factory=TuiConfig)
    auxiliary: AuxiliaryConfig = Field(default_factory=AuxiliaryConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """从字典创建配置，忽略未知字段。"""
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）。"""
        return self.model_dump(exclude_none=True)
