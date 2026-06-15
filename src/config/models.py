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
# 工具 DFX 配置
# ============================================================================

class ToolsConfig(BaseModel):
    """工具 DFX（Design for Excellence）配置段。

    设计理由：
    - max_tool_concurrency: 控制工具并行执行数量，防止系统过载
    - tool_result_budget: 截断大型工具结果，防止占满 LLM 上下文窗口
    - 两者均可通过环境变量覆盖（NANOHERMES_MAX_TOOL_CONCURRENCY / NANOHERMES_TOOL_RESULT_BUDGET）
    - 配置优先级：环境变量 > 配置文件 > 默认值
    """
    max_tool_concurrency: int | None = None
    tool_result_budget: int | None = None


# ============================================================================
# 后台任务配置
# ============================================================================

class MemoryFlushConfig(BaseModel):
    """记忆刷写任务配置。"""
    enabled: bool = True
    min_messages: int = 10


class SkillReviewConfig(BaseModel):
    """技能审查任务配置。"""
    enabled: bool = True
    min_turns: int = 10
    min_interval_minutes: int = 30
    curator_enabled: bool = True


class BackgroundTasksConfig(BaseModel):
    """后台任务配置段。

    设计理由：
    - enabled: 全局开关，可一键禁用所有后台任务
    - max_concurrent: 控制后台任务并发数，防止资源耗尽
    - task_timeout_seconds: 任务超时时间，防止任务无限运行
    - memory_flush / skill_review: 各任务的独立配置
    """
    enabled: bool = True
    max_concurrent: int = 2
    task_timeout_seconds: float = 300.0
    memory_flush: MemoryFlushConfig = Field(default_factory=MemoryFlushConfig)
    skill_review: SkillReviewConfig = Field(default_factory=SkillReviewConfig)


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
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    background_tasks: BackgroundTasksConfig = Field(default_factory=BackgroundTasksConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        """从字典创建配置，忽略未知字段。"""
        return cls.model_validate(data)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于序列化）。"""
        return self.model_dump(exclude_none=True)
