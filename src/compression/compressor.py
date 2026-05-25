"""ContextCompressor - 上下文压缩引擎。

当对话超出模型上下文窗口时：
1. 检测使用率（>50% 触发预压缩，>85% 强制压缩）
2. 使用辅助 LLM 生成摘要
3. 保护头部（system + 前 2 条消息）和尾部（最后 20 条消息）
4. 中间消息摘要化
"""

from __future__ import annotations

from typing import Any


# 摘要预算配置
_SUMMARY_BUDGET_RATIO = 0.20  # 20% 上下文用于摘要
_MIN_SUMMARY_TOKENS = 2000
_MAX_SUMMARY_TOKENS = 12000

# 保护范围
_PROTECT_HEAD_COUNT = 2  # 头部保护消息数
_PROTECT_TAIL_COUNT = 20  # 尾部保护消息数


class ContextCompressor:
    """上下文压缩引擎。

    当对话 token 数超过模型上下文窗口的阈值时触发压缩。
    """

    def __init__(
        self,
        context_window: int,
        pre_compress_threshold: float = 0.50,
        force_compress_threshold: float = 0.85,
    ):
        """初始化压缩器。

        Args:
            context_window: 模型上下文窗口大小（tokens）。
            pre_compress_threshold: 预压缩阈值（50%）。
            force_compress_threshold: 强制压缩阈值（85%）。
        """
        self._context_window = context_window
        self._pre_threshold = pre_compress_threshold
        self._force_threshold = force_compress_threshold

    def needs_compression(self, current_tokens: int) -> bool:
        """检查是否需要压缩。

        Args:
            current_tokens: 当前对话 token 数。

        Returns:
            True 需要压缩。
        """
        ratio = current_tokens / self._context_window if self._context_window > 0 else 0
        return ratio >= self._force_threshold

    def needs_pre_compress(self, current_tokens: int) -> bool:
        """检查是否需要预压缩。

        Args:
            current_tokens: 当前对话 token 数。

        Returns:
            True 需要预压缩。
        """
        ratio = current_tokens / self._context_window if self._context_window > 0 else 0
        return ratio >= self._pre_threshold

    def calculate_summary_budget(self, available_tokens: int) -> int:
        """计算摘要 token 预算。

        Args:
            available_tokens: 可用于摘要的 token 数。

        Returns:
            摘要预算 token 数。
        """
        budget = int(available_tokens * _SUMMARY_BUDGET_RATIO)
        return max(_MIN_SUMMARY_TOKENS, min(budget, _MAX_SUMMARY_TOKENS))

    def compress(
        self,
        messages: list[dict[str, Any]],
        summary: str,
    ) -> list[dict[str, Any]]:
        """压缩消息列表。

        策略：
        1. 保留 system 消息
        2. 保留头部 N 条消息
        3. 插入摘要消息
        4. 保留尾部 M 条消息

        Args:
            messages: 原始消息列表。
            summary: 辅助 LLM 生成的摘要。

        Returns:
            压缩后的消息列表。
        """
        if not messages:
            return messages

        # 分离 system 消息
        system_msgs = [m for m in messages if m.get("role") == "system"]
        non_system = [m for m in messages if m.get("role") != "system"]

        # 头部和尾部
        head = non_system[:_PROTECT_HEAD_COUNT]
        tail = non_system[-_PROTECT_TAIL_COUNT:]

        # 避免头部和尾部重叠
        if len(head) + len(tail) > len(non_system):
            head = non_system
            tail = []

        # 构建压缩后的消息
        compressed = list(system_msgs)
        compressed.extend(head)

        # 插入摘要
        if summary:
            compressed.append({
                "role": "assistant",
                "content": f"[Context compressed: {summary}]",
            })

        compressed.extend(tail)
        return compressed

    def prune_tool_output(self, content: str, max_length: int = 500) -> str:
        """剪枝工具输出。

        Args:
            content: 工具输出内容。
            max_length: 最大保留长度。

        Returns:
            剪枝后的内容。
        """
        if len(content) <= max_length:
            return content
        return content[:max_length] + "\n... [truncated]"
