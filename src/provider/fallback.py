"""回退模型链。

当主模型遇到不可恢复的错误时，回退链按顺序尝试备用模型。

关键设计：
- 一次性激活：一旦回退成功，保持使用回退模型直到对话结束
  避免在主模型和回退模型之间反复振荡
- 按配置顺序尝试：先尝试第一个回退，失败后尝试第二个，以此类推
- 客户端重建：回退激活时需要重新构建客户端（不同的凭证和配置）

触发回退的错误类型：
- 401/403: 认证/授权错误（凭证失效）
- 429: 速率限制（超过配额）
- 500/502/503: 服务器错误
- 无效响应：模型返回格式错误的内容
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FallbackEntry:
    """回退链中的一个条目。

    Attributes:
        provider: 回退提供商的 ID（如 "openai", "anthropic"）。
        model: 回退模型的名称（如 "gpt-4o", "claude-sonnet-4"）。
    """
    provider: str
    model: str


class FallbackChain:
    """回退模型链管理器。

    维护一个有序的回退模型列表，支持一次性激活语义。

    状态机：
        IDLE → ACTIVATING → ACTIVATED
              (正在尝试)    (已激活，保持使用)

    一旦进入 ACTIVATED 状态，后续调用 try_fallback 直接返回 None，
    防止反复切换模型。

    Attributes:
        _entries: 回退模型列表，按尝试顺序排列。
        _activated: 是否已经激活过回退（一次性标志）。
        _active_entry: 当前激活的回退条目（激活后设置）。
    """

    def __init__(self, entries: list[FallbackEntry] | None = None):
        """初始化回退链。

        Args:
            entries: 回退模型列表，按尝试顺序排列。
                     None 或空列表表示禁用回退。
        """
        self._entries = entries or []
        self._activated = False
        self._active_entry: FallbackEntry | None = None

    @property
    def is_activated(self) -> bool:
        """是否已经激活过回退。

        Returns:
            True 表示回退已激活，不应再尝试新的回退。
        """
        return self._activated

    @property
    def active_fallback(self) -> FallbackEntry | None:
        """当前激活的回退条目。

        Returns:
            已激活的 FallbackEntry，如果未激活则返回 None。
        """
        return self._active_entry

    @property
    def has_fallbacks(self) -> bool:
        """是否有配置的回退模型。

        Returns:
            True 表示有至少一个回退模型可用。
        """
        return len(self._entries) > 0

    def try_fallback(self) -> FallbackEntry | None:
        """尝试下一个回退模型。

        如果已经激活过，返回 None（防止反复切换）。
        否则返回下一个未尝试的回退条目。

        Returns:
            下一个要尝试的 FallbackEntry，如果没有更多回退或已激活则返回 None。
        """
        # 已经激活过，不再尝试
        if self._activated:
            return None

        # 没有配置回退
        if not self._entries:
            return None

        return None  # 由调用方决定尝试哪个回退（按索引）

    def get_next(self, current_index: int = 0) -> FallbackEntry | None:
        """获取下一个要尝试的回退条目。

        Args:
            current_index: 当前已尝试到的索引（从 0 开始）。

        Returns:
            下一个 FallbackEntry，如果没有更多则返回 None。
        """
        if self._activated:
            return None

        next_index = current_index
        if next_index < len(self._entries):
            return self._entries[next_index]
        return None

    def activate(self, entry: FallbackEntry) -> None:
        """激活一个回退模型。

        激活后，is_activated 变为 True，后续 try_fallback 返回 None。

        Args:
            entry: 要激活的回退条目。
        """
        self._activated = True
        self._active_entry = entry

    def reset(self) -> None:
        """重置回退链状态。

        清除激活状态，允许重新尝试回退。
        通常在对话结束时调用。
        """
        self._activated = False
        self._active_entry = None
