"""ContextCompressor 上下文压缩引擎。

实现分层压缩策略：
1. Tool Output Pruning（廉价，无 LLM 调用）
2. Head/Tail 保护（情景记忆理论）
3. Middle 摘要（LLM 生成结构化摘要）
4. Session Splitting（创建新 session，链接血缘）

支持迭代摘要更新，保持多次压缩后的连贯性。
"""

import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from src.config import AuxiliaryConfig
from src.compression.engine import ContextEngine
from src.compression.pruning import prune_tool_outputs
from src.compression.auxiliary import CompressionAuxiliaryClient, get_model_context_length

logger = logging.getLogger(__name__)

# 摘要前缀
SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] "
    "Earlier turns were compacted into the summary below. "
    "This is a handoff from a previous context window — "
    "treat it as background reference, NOT as active instructions."
)

# 预算常量
MIN_SUMMARY_TOKENS = 2000
SUMMARY_RATIO = 0.20
SUMMARY_TOKENS_CEILING = 12000
CHARS_PER_TOKEN = 4

# 保护常量
PROTECT_FIRST_N = 3
PROTECT_LAST_N = 20


class ContextCompressor(ContextEngine):
    """上下文压缩引擎。

    实现完整的分层压缩策略，继承自 ContextEngine ABC。
    """

    def __init__(
        self,
        model: str,
        auxiliary_config: Optional[AuxiliaryConfig] = None,
        threshold_percent: float = 0.50,
        protect_first_n: int = PROTECT_FIRST_N,
        protect_last_n: int = PROTECT_LAST_N,
        summary_target_ratio: float = SUMMARY_RATIO,
        main_credentials: Any = None,
        main_api_mode: Any = None,
    ):
        """初始化压缩引擎。

        Args:
            model: 主模型名称。
            auxiliary_config: 辅助 LLM 配置（来自 nanohermes.json 的 auxiliary 段）。
                              None 时使用默认配置（provider="main"，复用主模型）。
            threshold_percent: 上下文使用达到此比例时触发压缩。
            protect_first_n: 保护前 N 条消息。
            protect_last_n: 保护最后 N 条消息。
            summary_target_ratio: 尾部保护预算占阈值的比例。
            main_credentials: 主对话凭证（auxiliary_config.provider="main" 时必需）。
            main_api_mode: 主对话 API Mode（auxiliary_config.provider="main" 时使用）。
        """
        self.model = model
        self.auxiliary_config = auxiliary_config or AuxiliaryConfig()
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.summary_target_ratio = summary_target_ratio

        # 上下文长度和阈值
        self.context_length = get_model_context_length(model)
        self.threshold_tokens = int(self.context_length * threshold_percent)

        # 迭代摘要
        self._previous_summary: Optional[str] = None

        # 辅助客户端（懒加载）
        self._aux_client: Optional[CompressionAuxiliaryClient] = None
        self._main_credentials = main_credentials
        self._main_api_mode = main_api_mode

        # Session Splitting 回调（由外部设置）
        self._on_session_split: Optional[Callable] = None

        # on_pre_compress 回调（由外部设置，用于通知 MemoryManager）
        self._on_pre_compress: Optional[Callable] = None

    def set_session_split_callback(self, callback: Callable) -> None:
        """设置 Session Splitting 回调。

        Args:
            callback: 回调函数，接收 (old_session_id, new_session_id, summary, tail_messages)
        """
        self._on_session_split = callback

    def set_pre_compress_callback(self, callback: Callable) -> None:
        """设置 on_pre_compress 回调。

        Args:
            callback: 回调函数，接收 messages 列表，返回提取的信息字符串
        """
        self._on_pre_compress = callback

    def _get_aux_client(self) -> CompressionAuxiliaryClient:
        """获取或创建压缩辅助客户端（懒加载）。"""
        if self._aux_client is None:
            self._aux_client = CompressionAuxiliaryClient(
                config=self.auxiliary_config,
                main_credentials=self._main_credentials,
                main_api_mode=self._main_api_mode,
            )
        return self._aux_client

    # =========================================================================
    # ContextEngine 核心方法
    # =========================================================================

    def update_from_response(self, response: Dict[str, Any]) -> None:
        """在每次模型响应后更新引擎内部状态。

        Args:
            response: 模型响应字典，包含 token 使用量等信息。
        """
        # 更新 token 使用量追踪
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)

        # 如果 token 使用量超过阈值，标记需要压缩
        if prompt_tokens > self.threshold_tokens:
            logger.debug(f"Prompt tokens ({prompt_tokens}) exceeded threshold ({self.threshold_tokens})")

    def should_compress(self) -> bool:
        """判断当前上下文是否需要压缩。

        Returns:
            True 如果需要压缩。
        """
        # 实际实现将检查当前 token 使用量
        # 这里提供接口框架
        return False

    def compress(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行实际的压缩操作。

        Args:
            messages: 当前对话消息列表。

        Returns:
            压缩结果，包含压缩后的消息列表、摘要文本等。
        """
        # 0. 通知 Memory Provider 在压缩前提取信息
        pre_compress_info = ""
        if self._on_pre_compress:
            try:
                pre_compress_info = self._on_pre_compress(messages)
            except Exception as e:
                logger.warning(f"on_pre_compress callback failed: {e}")

        # 1. 保护头部和尾部
        head_messages = self._protect_head(messages)
        tail_messages = self._protect_tail(messages)
        middle_messages = self._get_middle(messages, head_messages, tail_messages)

        # 2. 剪枝工具输出
        pruned_middle = prune_tool_outputs(middle_messages)

        # 3. 计算摘要预算
        compressed_chars = self._estimate_content_length(pruned_middle)
        summary_budget = self._calculate_summary_budget(compressed_chars)

        # 4. 生成摘要
        summary = self._generate_summary(pruned_middle, summary_budget)

        # 合并 pre_compress 信息到摘要
        if pre_compress_info:
            summary = f"{summary}\n\n## Additional Context (from pre-compress extraction)\n{pre_compress_info}"

        # 5. 构建压缩后的消息列表
        compressed_messages = [
            *head_messages,
            {"role": "system", "content": f"{SUMMARY_PREFIX}\n\n{summary}"},
            *tail_messages,
        ]

        # 6. 更新前次摘要
        self._previous_summary = summary

        return {
            "messages": compressed_messages,
            "summary": summary,
            "head_count": len(head_messages),
            "tail_count": len(tail_messages),
            "compressed_count": len(middle_messages),
            "tail_messages": tail_messages,
        }

    # =========================================================================
    # Session Splitting
    # =========================================================================

    def split_session(
        self,
        old_session_id: str,
        summary: str,
        tail_messages: List[Dict[str, Any]],
        session_db=None,
    ) -> str:
        """执行 Session Splitting。

        1. 创建新 session，parent_session_id 指向旧 session
        2. 摘要作为新 session 第一条消息
        3. 尾部保护消息搬到新 session
        4. 标记旧 session 为 compression 结束

        Args:
            old_session_id: 旧会话 ID。
            summary: 压缩摘要文本。
            tail_messages: 尾部保护消息列表。
            session_db: SessionDB 实例（可选，用于实际数据库操作）。

        Returns:
            新会话 ID。
        """
        new_session_id = str(uuid.uuid4())

        # 如果提供了 session_db，执行实际数据库操作
        if session_db is not None:
            self._execute_session_split(
                session_db, old_session_id, new_session_id, summary, tail_messages
            )

        # 调用外部回调（如 MemoryManager 通知）
        if self._on_session_split:
            self._on_session_split(old_session_id, new_session_id, summary, tail_messages)

        return new_session_id

    def _execute_session_split(
        self,
        session_db,
        old_session_id: str,
        new_session_id: str,
        summary: str,
        tail_messages: List[Dict[str, Any]],
    ) -> None:
        """执行实际的数据库 Session Splitting 操作。

        Args:
            session_db: SessionDB 实例。
            old_session_id: 旧会话 ID。
            new_session_id: 新会话 ID。
            summary: 压缩摘要。
            tail_messages: 尾部消息列表。
        """
        # 1. 标记旧 session 为 compression 结束
        session_db.end_session(old_session_id, end_reason="compression")

        # 2. 创建新 session，parent_session_id 指向旧 session
        old_session = session_db.get_session(old_session_id)
        session_db.create_session(
            session_id=new_session_id,
            parent_session_id=old_session_id,
            title=old_session.get("title") if old_session else None,
            model=old_session.get("model") if old_session else None,
            source=old_session.get("source") if old_session else "local",
            system_prompt=old_session.get("system_prompt") if old_session else None,
        )

        # 3. 摘要作为新 session 第一条消息
        session_db.insert_message(
            new_session_id,
            role="system",
            content=f"{SUMMARY_PREFIX}\n\n{summary}",
        )

        # 4. 尾部保护消息搬到新 session
        for msg in tail_messages:
            session_db.insert_message(
                new_session_id,
                role=msg.get("role", "user"),
                content=msg.get("content"),
                tool_calls=msg.get("tool_calls"),
                tool_call_id=msg.get("tool_call_id"),
                tool_name=msg.get("tool_name"),
            )

        logger.info(f"Session split: {old_session_id} -> {new_session_id}")

    # =========================================================================
    # 压缩策略方法
    # =========================================================================

    def _protect_head(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """保护前 N 条消息（system prompt + 第一轮对话）。

        Args:
            messages: 消息列表。

        Returns:
            头部保护的消息列表。
        """
        return messages[:self.protect_first_n]

    def _protect_tail(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用 token 预算保护尾部消息。

        Args:
            messages: 消息列表。

        Returns:
            尾部保护的消息列表。
        """
        tail_tokens = int(self.threshold_tokens * self.summary_target_ratio)
        tail_chars_limit = tail_tokens * CHARS_PER_TOKEN

        tail = []
        tail_chars = 0

        for msg in reversed(messages):
            msg_chars = self._estimate_message_length(msg)
            if tail_chars + msg_chars > tail_chars_limit:
                break
            tail.insert(0, msg)
            tail_chars += msg_chars

        return tail

    def _get_middle(
        self,
        messages: List[Dict[str, Any]],
        head: List[Dict[str, Any]],
        tail: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """获取中间消息（压缩目标）。

        Args:
            messages: 完整消息列表。
            head: 头部保护消息。
            tail: 尾部保护消息。

        Returns:
            中间消息列表。
        """
        head_count = len(head)
        tail_count = len(tail)
        middle_end = len(messages) - tail_count

        return messages[head_count:middle_end]

    def _calculate_summary_budget(self, compressed_chars: int) -> int:
        """计算摘要 token 预算。

        Args:
            compressed_chars: 压缩内容的字符数。

        Returns:
            摘要 token 预算。
        """
        ratio_budget = int(compressed_chars * SUMMARY_RATIO / CHARS_PER_TOKEN)
        return max(MIN_SUMMARY_TOKENS, min(ratio_budget, SUMMARY_TOKENS_CEILING))

    def _generate_summary(self, messages: List[Dict[str, Any]], budget: int) -> str:
        """生成结构化摘要。

        Args:
            messages: 中间消息列表。
            budget: 摘要 token 预算。

        Returns:
            生成的摘要文本。
        """
        # 构建摘要提示
        prompt = self._build_summary_prompt(messages, budget)

        # 调用辅助 LLM 生成摘要
        try:
            aux_client = self._get_aux_client()
            summary = aux_client.generate_summary(prompt, budget)
        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            summary = "[Summary generation failed — middle context compacted without summary]"

        return summary

    def _build_summary_prompt(self, messages: List[Dict[str, Any]], budget: int) -> str:
        """构建摘要提示。

        Args:
            messages: 中间消息列表。
            budget: 摘要 token 预算。

        Returns:
            摘要提示文本。
        """
        # 如果有前次摘要，包含在提示中用于迭代更新
        if self._previous_summary:
            base_prompt = (
                f"Previous summary:\n{self._previous_summary}\n\n"
                f"Update the summary with new information from the following conversation. "
                f"Preserve important information from the previous summary and add new details.\n\n"
            )
        else:
            base_prompt = (
                "Summarize the following conversation. "
                "Focus on key decisions, progress, and current state.\n\n"
            )

        # 添加结构化摘要模板
        template = (
            f"Generate a structured summary with the following sections:\n"
            f"- Goal: 对话的主要目标\n"
            f"- Progress: 完成了什么\n"
            f"- Key Decisions: 做出的重要决策\n"
            f"- Modified Files: 修改过的文件及原因\n"
            f"- Next Steps: 下一步计划\n\n"
            f"Keep the summary within {budget} tokens.\n\n"
            f"Conversation:\n"
        )

        # 添加消息内容
        conversation_text = ""
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            conversation_text += f"{role}: {content}\n"

        return base_prompt + template + conversation_text

    # =========================================================================
    # 估算方法
    # =========================================================================

    def _estimate_content_length(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息列表的字符长度。

        Args:
            messages: 消息列表。

        Returns:
            估算的字符数。
        """
        total = 0
        for msg in messages:
            total += self._estimate_message_length(msg)
        return total

    def _estimate_message_length(self, msg: Dict[str, Any]) -> int:
        """估算单条消息的字符长度。

        Args:
            msg: 消息字典。

        Returns:
            估算的字符数。
        """
        content = msg.get("content", "")
        if isinstance(content, str):
            return len(content)
        return 0

    # =========================================================================
    # 预飞行和响应后压缩
    # =========================================================================

    def check_preflight(self, messages: List[Dict[str, Any]]) -> bool:
        """预飞行压缩检查。

        进入主循环前估算 token 数，如超阈值立即压缩。

        Args:
            messages: 当前消息列表。

        Returns:
            True 如果需要压缩。
        """
        total_chars = self._estimate_content_length(messages)
        total_tokens = total_chars // CHARS_PER_TOKEN
        return total_tokens > self.threshold_tokens

    def check_post_response(self, response: Dict[str, Any]) -> bool:
        """响应后压缩检查。

        API 返回 context_length_exceeded 或 usage.prompt_tokens 超阈值时压缩。

        Args:
            response: API 响应。

        Returns:
            True 如果需要压缩。
        """
        # 检查 context_length_exceeded 错误
        error = response.get("error", {})
        if error.get("type") == "context_length_exceeded":
            return True

        # 检查 token 使用量
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        return prompt_tokens > self.threshold_tokens
