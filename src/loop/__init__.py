"""循环执行模块。

提供 /loop 命令支持，让 AI Agent 在会话内自动重复执行任务。

核心组件：
- LoopConfig: 循环配置（间隔、提示、模式）
- LoopState: 循环运行时状态
- LoopStatus: 循环状态枚举
- LoopManager: 循环生命周期管理
- parse_interval: 间隔表达式解析
- get_maintenance_prompt: 内置维护提示加载

设计理由：
- 循环管理是独立关注点，不属于对话循环、TUI 或工具系统
- 复用现有 ConversationLoop 执行机制，不重复实现
- 循环作用域限定在当前会话，支持 --resume 恢复（7 天内）
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


class LoopMode(Enum):
    """循环调度模式。

    FIXED: 固定间隔（用户指定或解析后的 cron 表达式）
    DYNAMIC: 动态间隔（AI 根据上下文自行决定等待时间）
    """
    FIXED = "fixed"
    DYNAMIC = "dynamic"


class LoopStatus(Enum):
    """循环生命周期状态。

    CREATED: 已创建，尚未开始执行
    ACTIVE: 活跃，正在等待或执行中
    WAITING: 等待下一次间隔到期
    EXECUTING: 正在执行对话循环
    STOPPED: 用户手动停止
    EXPIRED: 超过 7 天自动过期
    ERROR: 执行出错（不停止循环，仅标记）
    """
    CREATED = "created"
    ACTIVE = "active"
    WAITING = "waiting"
    EXECUTING = "executing"
    STOPPED = "stopped"
    EXPIRED = "expired"
    ERROR = "error"


# 循环 ID 长度（8 字符，与 Claude Code 一致）
LOOP_ID_LENGTH = 8

# 循环过期时间（7 天）
LOOP_EXPIRY_DAYS = 7

# 最小间隔（60 秒 = 1 分钟）
MIN_INTERVAL_SECONDS = 60

# 最大间隔（86400 秒 = 24 小时）
MAX_INTERVAL_SECONDS = 86400

# 默认动态间隔（当 AI 未输出 __next_interval 标记时使用）
DEFAULT_DYNAMIC_INTERVAL = 600  # 10 分钟

# loop.md 最大大小（25,000 字节）
MAX_LOOP_MD_SIZE = 25_000


def generate_loop_id() -> str:
    """生成唯一的循环 ID（8 字符）。"""
    return uuid.uuid4().hex[:LOOP_ID_LENGTH]


@dataclass
class LoopConfig:
    """循环配置。

    不可变配置，创建后不改变。
    """
    loop_id: str = field(default_factory=generate_loop_id)
    interval_seconds: Optional[int] = None  # None 表示动态模式
    prompt: Optional[str] = None  # None 表示使用维护提示
    mode: LoopMode = LoopMode.DYNAMIC
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def expires_at(self) -> datetime:
        """循环过期时间（创建后 7 天）。"""
        return self.created_at + timedelta(days=LOOP_EXPIRY_DAYS)

    @property
    def is_expired(self) -> bool:
        """检查是否已过期。"""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_dynamic(self) -> bool:
        """是否是动态间隔模式。"""
        return self.mode == LoopMode.DYNAMIC or self.interval_seconds is None

    def to_meta_dict(self) -> dict:
        """转换为可序列化的字典（用于 JSONL 存储）。"""
        return {
            "loop_id": self.loop_id,
            "interval_seconds": self.interval_seconds,
            "prompt": self.prompt,
            "mode": self.mode.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }

    @classmethod
    def from_meta_dict(cls, data: dict) -> "LoopConfig":
        """从序列化字典恢复配置。"""
        return cls(
            loop_id=data["loop_id"],
            interval_seconds=data.get("interval_seconds"),
            prompt=data.get("prompt"),
            mode=LoopMode(data.get("mode", "dynamic")),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class LoopState:
    """循环运行时状态。

    可变状态，随循环执行而更新。
    """
    config: LoopConfig
    status: LoopStatus = LoopStatus.CREATED
    last_executed_at: Optional[datetime] = None
    last_error: Optional[str] = None
    execution_count: int = 0

    @property
    def loop_id(self) -> str:
        return self.config.loop_id

    @property
    def is_active(self) -> bool:
        """是否处于活跃状态（可继续执行）。"""
        return self.status in (
            LoopStatus.CREATED,
            LoopStatus.ACTIVE,
            LoopStatus.WAITING,
            LoopStatus.ERROR,
        )

    def to_meta_dict(self) -> dict:
        """转换为可序列化的字典。"""
        data = self.config.to_meta_dict()
        data.update({
            "status": self.status.value,
            "last_executed_at": self.last_executed_at.isoformat() if self.last_executed_at else None,
            "last_error": self.last_error,
            "execution_count": self.execution_count,
        })
        return data
