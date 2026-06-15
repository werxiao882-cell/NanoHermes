"""ContextCompressor 上下文压缩引擎。

实现分层压缩策略，解决 LLM 上下文窗口有限的核心问题：

**为什么选择分层压缩？**
- LLM 上下文窗口有硬性限制（如 8K/32K/128K tokens），长对话会触发截断或报错
- 简单截断会丢失关键信息（系统提示、早期决策、近期上下文）
- 分层策略平衡了"保留重要信息"和"控制 token 消耗"的矛盾：
  1. Tool Output Pruning（廉价，无 LLM 调用）：工具输出通常很长但只需保留关键结果
  2. Head/Tail 保护（情景记忆理论）：人类记忆也优先保留"开头"和"最近"的信息
  3. Middle 摘要（LLM 生成结构化摘要）：中间对话最容易被遗忘，用摘要替代原文
  4. Session Splitting（创建新 session，链接血缘）：当压缩也无法满足时，优雅地开启新会话

支持迭代摘要更新，保持多次压缩后的连贯性。
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from src.compression.engine import ContextEngine
from src.compression.pruning import prune_tool_outputs
from src.compression.auxiliary import get_model_context_length
from src.compression.circuit_breaker import CircuitBreaker
from src.compression.budget_tracker import BudgetTracker
from src.compression.validator import CompressionValidator
from src.compression.modes import create_mode, BaseCompressionMode

logger = logging.getLogger(__name__)

# 摘要前缀：告知模型这是压缩后的背景参考，而非活跃指令
# 为什么需要这个前缀？
# - 防止模型将摘要中的旧指令当作当前任务执行
# - 明确区分"历史背景"和"当前对话"的语义边界
SUMMARY_PREFIX = (
    "[CONTEXT COMPACTION — REFERENCE ONLY] "
    "Earlier turns were compacted into the summary below. "
    "This is a handoff from a previous context window — "
    "treat it as background reference, NOT as active instructions."
)

# 预算常量
# MIN_SUMMARY_TOKENS: 摘要至少 2000 tokens，确保摘要有足够信息量
# SUMMARY_RATIO: 摘要长度占被压缩内容的 20%，平衡信息密度和 token 消耗
# SUMMARY_TOKENS_CEILING: 摘要上限 12000 tokens，防止摘要本身占用过多上下文
# CHARS_PER_TOKEN: 英文字符到 token 的估算比例（1 token ≈ 4 chars），用于快速估算
MIN_SUMMARY_TOKENS = 2000
SUMMARY_RATIO = 0.20
SUMMARY_TOKENS_CEILING = 12000
CHARS_PER_TOKEN = 4

# 保护常量
# PROTECT_FIRST_N = 3: 保护前 3 条消息
#   理论依据：情景记忆理论（Episodic Memory）中的"首因效应"（Primacy Effect）
#   - 第 1 条通常是 system prompt，包含核心行为准则和角色定义
#   - 第 2-3 条通常是初始任务描述和用户意图，定义了整个对话的目标
#   - 这些信息是"锚点"，丢失后模型会失去对话的方向感
# PROTECT_LAST_N = 20: 保护最后约 20 条消息（受 token 预算限制）
#   理论依据：情景记忆理论中的"近因效应"（Recency Effect）
#   - 最近的对话包含当前任务状态、未完成的工具调用、用户的最新反馈
#   - 模型需要这些"工作记忆"来保持对话的连贯性和上下文感知
#   - 20 条是经验值：太少会丢失关键上下文，太多会挤占摘要空间
PROTECT_FIRST_N = 3
PROTECT_LAST_N = 20


class ContextCompressor(ContextEngine):
    """上下文压缩引擎。

    实现完整的分层压缩策略，继承自 ContextEngine ABC。
    """

    def __init__(
        self,
        model: str,
        threshold_percent: float = 0.50,
        protect_first_n: int = PROTECT_FIRST_N,
        protect_last_n: int = PROTECT_LAST_N,
        summary_target_ratio: float = SUMMARY_RATIO,
        # 新增：熔断器参数
        enable_circuit_breaker: bool = True,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_cooldown: float = 60.0,
        # 新增：预算追踪器参数
        enable_budget_tracker: bool = True,
        budget_tracker_max_history: int = 100,
        # 新增：压缩验证器参数
        enable_validator: bool = True,
        validator_min_retention: float = 0.6,
        validator_min_length: int = 500,
        validator_max_length: int = 12000,
        # 新增：压缩模式参数
        compression_mode: str = "reactive",
        reactive_threshold: float = 0.5,
        micro_interval: int = 10,
        snip_patterns: Optional[List[str]] = None,
    ):
        """初始化压缩引擎。

        **参数设计理由：**

        - model: 主模型名称，用于获取上下文长度
        - threshold_percent: 上下文使用达到此比例时触发压缩
            * 默认 50%：在上下文使用一半时开始准备压缩
            * 为什么不是 80% 或 90%？因为需要预留空间给：
              - 用户的新消息
              - 模型的回答
              - 工具调用的输出
            * 50% 是保守值，确保有足够的缓冲空间
        - protect_first_n: 保护前 N 条消息（默认 3）
        - protect_last_n: 保护最后 N 条消息（默认 20，受 token 预算限制）
        - summary_target_ratio: 尾部保护预算占阈值的比例（默认 20%）
            * 尾部和摘要共享这个比例，两者竞争相同的 token 空间
            * 20% 是经验值：既能保护足够的上下文，又留给摘要 30% 的空间

        新增参数：
        - enable_circuit_breaker: 是否启用熔断器（默认 True）
        - circuit_breaker_threshold: 熔断器失败阈值（默认 3 次）
        - circuit_breaker_cooldown: 熔断器冷却期（默认 60 秒）
        - enable_budget_tracker: 是否启用预算追踪器（默认 True）
        - budget_tracker_max_history: 预算追踪器最大历史记录数（默认 100）
        - enable_validator: 是否启用压缩验证器（默认 True）
        - validator_min_retention: 验证器最小信息保留率（默认 0.6）
        - validator_min_length: 验证器最小摘要长度（默认 500 字符）
        - validator_max_length: 验证器最大摘要长度（默认 12000 字符）
        - compression_mode: 压缩模式（"reactive"、"micro"、"snip"，默认 "reactive"）
        - reactive_threshold: Reactive 模式触发阈值（默认 0.5）
        - micro_interval: Micro 模式触发间隔（默认 10 轮）
        - snip_patterns: Snip 模式触发模式列表（默认 None）

        Args:
            model: 主模型名称。
            threshold_percent: 上下文使用达到此比例时触发压缩。
            protect_first_n: 保护前 N 条消息。
            protect_last_n: 保护最后 N 条消息。
            summary_target_ratio: 尾部保护预算占阈值的比例。
            enable_circuit_breaker: 是否启用熔断器。
            circuit_breaker_threshold: 熔断器失败阈值。
            circuit_breaker_cooldown: 熔断器冷却期（秒）。
            enable_budget_tracker: 是否启用预算追踪器。
            budget_tracker_max_history: 预算追踪器最大历史记录数。
            enable_validator: 是否启用压缩验证器。
            validator_min_retention: 验证器最小信息保留率。
            validator_min_length: 验证器最小摘要长度。
            validator_max_length: 验证器最大摘要长度。
            compression_mode: 压缩模式名称。
            reactive_threshold: Reactive 模式触发阈值。
            micro_interval: Micro 模式触发间隔。
            snip_patterns: Snip 模式触发模式列表。
        """
        self.model = model
        self.threshold_percent = threshold_percent
        self.protect_first_n = protect_first_n
        self.protect_last_n = protect_last_n
        self.summary_target_ratio = summary_target_ratio

        # 上下文长度和阈值
        # 从模型名称获取上下文长度（如 qwen-turbo 是 8K，qwen-plus 是 32K）
        self.context_length = get_model_context_length(model)
        # 触发压缩的 token 阈值 = 上下文长度 * 百分比
        self.threshold_tokens = int(self.context_length * threshold_percent)

        # 迭代摘要：保存上次压缩的摘要，用于下次压缩时的迭代更新
        self._previous_summary: Optional[str] = None

        # Session Splitting 回调（由外部设置）
        # 为什么用回调而非直接调用？
        # - 解耦：compressor 不应该直接依赖 session_db
        # - 灵活性：外部可以决定如何处理 session splitting
        self._on_session_split: Optional[Callable] = None

        # on_pre_compress 回调（由外部设置，用于通知 MemoryManager）
        # 在压缩前提取关键信息（如文件变更、用户偏好）
        self._on_pre_compress: Optional[Callable] = None

        # 新增：初始化熔断器
        # 设计理由：防止压缩循环，连续失败后自动降级
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if enable_circuit_breaker:
            self._circuit_breaker = CircuitBreaker(
                failure_threshold=circuit_breaker_threshold,
                cooldown_seconds=circuit_breaker_cooldown,
            )

        # 新增：初始化预算追踪器
        # 设计理由：监控压缩效率，提供可观测性
        self._budget_tracker: Optional[BudgetTracker] = None
        if enable_budget_tracker:
            self._budget_tracker = BudgetTracker(
                max_history=budget_tracker_max_history,
            )

        # 新增：初始化压缩验证器
        # 设计理由：验证压缩质量，避免过度压缩
        self._validator: Optional[CompressionValidator] = None
        if enable_validator:
            self._validator = CompressionValidator(
                min_retention_rate=validator_min_retention,
                min_summary_length=validator_min_length,
                max_summary_length=validator_max_length,
            )

        # 新增：初始化压缩模式
        # 设计理由：支持多种触发策略，适应不同场景
        self._compression_mode: BaseCompressionMode = create_mode(
            mode_name=compression_mode,
            reactive_threshold=reactive_threshold,
            micro_interval=micro_interval,
            snip_patterns=snip_patterns,
        )

        # 对话轮次计数器（用于 Micro 模式）
        self._turn_count = 0

    def set_session_split_callback(self, callback: Callable) -> None:
        """设置 Session Splitting 回调。

        **回调的作用：**
        - 当 compressor 决定 split session 时，通知外部组件
        - 外部组件可以执行额外操作（如更新记忆文件、通知 UI）

        Args:
            callback: 回调函数，接收 (old_session_id, new_session_id, summary, tail_messages)
        """
        self._on_session_split = callback

    def set_pre_compress_callback(self, callback: Callable) -> None:
        """设置 on_pre_compress 回调。

        **回调的作用：**
        - 在压缩前提取关键信息（如文件变更、用户偏好）
        - 这是"最后机会"钩子，在消息被摘要化之前提取结构化数据

        Args:
            callback: 回调函数，接收 messages 列表，返回提取的信息字符串
        """
        self._on_pre_compress = callback



    # =========================================================================
    # ContextEngine 核心方法
    # =========================================================================

    def update_from_response(self, response: Dict[str, Any]) -> None:
        """在每次模型响应后更新引擎内部状态。

        **为什么需要更新状态？**
        - 跟踪 token 使用量，判断是否需要压缩
        - 在每次 API 响应后检查是否接近阈值

        Args:
            response: 模型响应字典，包含 token 使用量等信息。
        """
        # 更新 token 使用量追踪
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)

        # 如果 token 使用量超过阈值，标记需要压缩
        # 注意：这里只是记录日志，实际压缩决策由 should_compress() 和 check_post_response() 负责
        if prompt_tokens > self.threshold_tokens:
            logger.debug(f"Prompt tokens ({prompt_tokens}) exceeded threshold ({self.threshold_tokens})")

    def should_compress(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        current_tokens: Optional[int] = None,
    ) -> bool:
        """判断当前上下文是否需要压缩。

        根据配置的压缩模式判断是否触发压缩：
        - Reactive 模式：基于 token 使用率
        - Micro 模式：基于对话轮次
        - Snip 模式：基于消息内容特征

        Args:
            messages: 当前对话消息列表（用于 Snip 模式）。
            current_tokens: 当前 token 数（用于 Reactive 模式）。

        Returns:
            True 如果需要压缩。
        """
        # 如果启用了熔断器且处于 OPEN 状态，拒绝压缩
        if self._circuit_breaker and not self._circuit_breaker.can_compress():
            logger.debug("Circuit breaker is OPEN, skipping compression")
            return False

        # 使用压缩模式判断
        return self._compression_mode.should_compress(
            messages=messages or [],
            current_tokens=current_tokens,
            max_tokens=self.context_length,
            turn_count=self._turn_count,
        )

    def increment_turn_count(self) -> None:
        """增加对话轮次计数（用于 Micro 模式）。

        应在每次对话轮次结束后调用。
        """
        self._turn_count += 1

    def compress(
        self,
        messages: List[Dict[str, Any]],
        current_tokens: int | None = None,
        focus_topic: str | None = None,
        force: bool = False,
        model_caller=None,
    ) -> Dict[str, Any]:
        """执行实际的压缩操作。

        **压缩流程设计理由：**
        1. 检查熔断器：如果处于 OPEN 状态，拒绝压缩
        2. 预压缩回调：给 Memory Provider 机会提取关键信息（如文件变更、待办事项）
        3. 保护头尾：基于情景记忆理论，保留对话的"锚点"和"工作记忆"
        4. 工具输出剪枝：工具输出通常很长（如文件内容、命令输出），但只需保留关键结果
        5. 摘要预算：根据被压缩内容动态计算，避免摘要过长或过短
        6. 生成摘要：使用辅助 LLM（不占用主模型配额）生成结构化摘要
        7. 合并消息：头部 + 摘要 + 尾部，形成新的上下文窗口
        8. 验证质量：检查信息保留度和摘要长度
        9. 记录统计：更新预算追踪器和熔断器状态

        Args:
            messages: 当前对话消息列表。
            current_tokens: 当前 token 估算数（可选）。
            focus_topic: 焦点主题（可选，用于焦点压缩）。
            force: 是否强制压缩（忽略阈值检查）。
            model_caller: 模型调用函数（可选，用于摘要生成）。

        Returns:
            压缩结果字典，包含 messages、summary、统计信息等。
        """
        # 新增：检查熔断器状态
        if self._circuit_breaker and not self._circuit_breaker.can_compress():
            logger.warning("Circuit breaker is OPEN, skipping compression")
            return {
                "messages": messages,
                "summary": "",
                "head_count": 0,
                "tail_count": 0,
                "compressed_count": 0,
                "tail_messages": [],
                "skipped": True,
                "reason": "circuit_breaker_open",
                "circuit_breaker_state": self._circuit_breaker.state,
            }

        # 记录压缩开始时间（用于预算追踪）
        start_time = time.time()

        try:
            # 0. 通知 Memory Provider 在压缩前提取信息
            # 为什么需要预压缩回调？
            # - Memory Provider 可能想从即将被压缩的消息中提取关键信息
            # - 例如：记录修改过的文件列表、提取用户偏好、更新 USER.md
            # - 这是一个"最后机会"钩子，在消息被摘要化之前提取结构化数据
            pre_compress_info = ""
            if self._on_pre_compress:
                try:
                    pre_compress_info = self._on_pre_compress(messages)
                except Exception as e:
                    # 回调失败不应阻断压缩流程，仅记录警告
                    logger.warning(f"on_pre_compress callback failed: {e}")

            # 1. 保护头部和尾部
            # 将消息分为三部分：头部（不可变锚点）、尾部（工作记忆）、中间（可压缩）
            head_messages = self._protect_head(messages)
            tail_messages = self._protect_tail(messages)
            middle_messages = self._get_middle(messages, head_messages, tail_messages)

            # 2. 剪枝工具输出
            # 为什么先剪枝再生成摘要？
            # - 工具输出（如文件内容、命令输出）通常很长但信息密度低
            # - 剪枝可以大幅减少需要摘要的内容，降低 LLM 调用成本
            # - 摘要只需要知道"工具执行了什么"，不需要保留完整的输出内容
            pruned_middle = prune_tool_outputs(middle_messages)

            # 3. 计算摘要预算
            # 根据剪枝后的内容长度动态计算摘要应该占多少 tokens
            compressed_chars = self._estimate_content_length(pruned_middle)
            summary_budget = self._calculate_summary_budget(compressed_chars)

            # 4. 生成摘要
            # 使用主对话的 model_caller 生成结构化摘要
            summary = self._generate_summary(pruned_middle, summary_budget, model_caller)

            # 合并 pre_compress 信息到摘要
            # 将 Memory Provider 提取的结构化信息追加到摘要末尾
            # 这样模型既能看到 LLM 生成的自然语言摘要，也能看到结构化的关键数据
            if pre_compress_info:
                summary = f"{summary}\n\n## Additional Context (from pre-compress extraction)\n{pre_compress_info}"

            # 5. 构建压缩后的消息列表
            # 结构：[头部保护消息] + [摘要 system 消息] + [尾部保护消息]
            # 为什么摘要作为 system 消息？
            # - system 消息在对话中具有最高优先级，模型会将其视为背景知识
            # - 与用户/助手消息区分开，避免模型混淆"历史记录"和"当前对话"
            compressed_messages = [
                *head_messages,
                {"role": "system", "content": f"{SUMMARY_PREFIX}\n\n{summary}"},
                *tail_messages,
            ]

            # 6. 更新前次摘要
            # 保存当前摘要，用于下次压缩时的"迭代更新"
            # 迭代更新的优势：保持多次压缩后的信息连贯性，避免信息丢失
            self._previous_summary = summary

            # 新增：验证压缩质量
            validation_result = None
            if self._validator:
                validation_result = self._validator.validate(
                    original_messages=messages,
                    compressed_messages=compressed_messages,
                    summary=summary,
                )
                if not validation_result.is_valid:
                    logger.warning(
                        f"Compression validation failed: {validation_result.warnings}"
                    )
                    # 注意：验证失败不回滚，仅记录警告
                    # 原因：回滚会导致压缩循环，验证失败仍比不压缩好

            # 新增：记录压缩统计（预算追踪）
            compression_efficiency = 0.0
            if self._budget_tracker and current_tokens is not None:
                # 估算压缩后的 token 数
                after_tokens = self._estimate_tokens(compressed_messages)
                duration_ms = (time.time() - start_time) * 1000

                record = self._budget_tracker.track_compression(
                    before_tokens=current_tokens,
                    after_tokens=after_tokens,
                    success=True,
                    duration_ms=duration_ms,
                )
                compression_efficiency = self._budget_tracker.get_compression_efficiency()

            # 新增：记录成功到熔断器
            if self._circuit_breaker:
                self._circuit_breaker.record_success()

            return {
                "messages": compressed_messages,
                "summary": summary,
                "head_count": len(head_messages),
                "tail_count": len(tail_messages),
                "compressed_count": len(middle_messages),
                "tail_messages": tail_messages,
                # 新增字段
                "validation": validation_result.__dict__ if validation_result else None,
                "compression_efficiency": compression_efficiency,
                "circuit_breaker_state": self._circuit_breaker.state if self._circuit_breaker else None,
            }

        except Exception as e:
            # 新增：记录失败到熔断器和预算追踪器
            logger.error(f"Compression failed: {e}", exc_info=True)

            if self._circuit_breaker:
                self._circuit_breaker.record_failure()

            if self._budget_tracker and current_tokens is not None:
                duration_ms = (time.time() - start_time) * 1000
                self._budget_tracker.track_compression(
                    before_tokens=current_tokens,
                    after_tokens=current_tokens,  # 压缩失败，token 数不变
                    success=False,
                    duration_ms=duration_ms,
                )

            # 返回原始消息，标记压缩失败
            return {
                "messages": messages,
                "summary": "",
                "head_count": 0,
                "tail_count": 0,
                "compressed_count": 0,
                "tail_messages": [],
                "error": str(e),
                "circuit_breaker_state": self._circuit_breaker.state if self._circuit_breaker else None,
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

        **Session Splitting 的设计理由：**

        1. 什么时候需要 Splitting？
           - 当压缩后的消息仍然超过上下文窗口时
           - 当对话太长，即使压缩也无法保持足够的上下文
           - 当用户主动要求"清理上下文"或"开始新对话"

        2. Splitting vs Compression 的区别：
           - Compression：在同一个 session 内压缩消息，保持 session ID 不变
           - Splitting：创建新 session，将压缩摘要和尾部消息迁移到新 session
           - Splitting 是"终极手段"，当 compression 无法满足时使用

        3. 血缘关系（parent_session_id）：
           - 新 session 的 parent_session_id 指向旧 session
           - 支持会话历史追溯：可以回溯整个压缩链
           - 便于调试和分析：知道哪些 session 是由压缩产生的

        4. 数据迁移策略：
           - 旧 session 标记为 "compression" 结束（而非正常结束）
           - 摘要作为新 session 的第一条 system 消息
           - 尾部保护消息（工作记忆）完整迁移到新 session

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
        # 为什么 session_db 是可选的？
        # - 单元测试时可能不需要真实数据库
        # - 某些场景下只需要生成新 session ID，由外部处理存储
        if session_db is not None:
            self._execute_session_split(
                session_db, old_session_id, new_session_id, summary, tail_messages
            )

        # 调用外部回调（如 MemoryManager 通知）
        # 为什么需要回调？
        # - MemoryManager 可能需要更新记忆文件
        # - 外部组件可能需要知道 session 被 split 了
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

        **操作步骤详解：**

        1. 标记旧 session 为 compression 结束
           - end_reason="compression" 区分于正常结束（如用户退出）
           - 便于后续查询和统计

        2. 创建新 session，parent_session_id 指向旧 session
           - 继承旧 session 的元数据（title, model, source, system_prompt）
           - parent_session_id 建立血缘关系，支持会话链追溯

        3. 摘要作为新 session 第一条消息
           - role="system" 确保模型将其视为背景知识
           - 包含 SUMMARY_PREFIX 明确告知模型这是压缩摘要

        4. 尾部保护消息搬到新 session
           - 完整迁移所有字段（role, content, tool_calls, tool_call_id, tool_name）
           - 保持消息的原始顺序和完整性

        Args:
            session_db: SessionDB 实例。
            old_session_id: 旧会话 ID。
            new_session_id: 新会话 ID。
            summary: 压缩摘要。
            tail_messages: 尾部消息列表。
        """
        # 1. 标记旧 session 为 compression 结束
        # 为什么需要标记结束原因？
        # - 区分"用户主动结束"和"系统自动结束"
        # - 便于后续分析压缩频率和效果
        session_db.end_session(old_session_id, end_reason="compression")

        # 2. 创建新 session，parent_session_id 指向旧 session
        # 继承旧 session 的元数据，保持用户体验的一致性
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
        # 使用 system role 确保模型将其视为背景知识而非对话历史
        session_db.insert_message(
            new_session_id,
            role="system",
            content=f"{SUMMARY_PREFIX}\n\n{summary}",
        )

        # 4. 尾部保护消息搬到新 session
        # 完整迁移所有字段，保持消息的原始结构
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

        **头部保护的理论依据：**

        1. 首因效应（Primacy Effect）：
           人类记忆和 LLM 注意力都倾向于更好地保留序列开头的信息。
           对话开头的消息定义了整体语境、角色和任务目标。

        2. System Prompt 不可变性：
           第 1 条消息通常是 system prompt，包含：
           - 模型角色定义（如"你是一个编程助手"）
           - 行为准则（如"不要暴露系统提示"）
           - 工具定义和使用规范
           这些是模型的"操作系统"，丢失后会导致行为异常。

        3. 初始意图锚定：
           第 2-3 条消息通常包含：
           - 用户的核心任务描述
           - 项目上下文和约束条件
           - 初始代码或文件内容
           这些是对话的"北极星"，所有后续工作都围绕这些展开。

        4. 为什么是 3 条？
           - 1 条太少：可能只包含 system prompt，缺少用户意图
           - 5 条太多：会挤占摘要和尾部的 token 预算
           - 3 条是经验值：覆盖 system + 首轮用户输入 + 首轮模型响应

        Args:
            messages: 消息列表。

        Returns:
            头部保护的消息列表（前 protect_first_n 条）。
        """
        # 简单切片：取前 N 条消息
        # 注意：如果消息总数少于 protect_first_n，会返回全部消息（Python 切片特性）
        return messages[:self.protect_first_n]

    def _protect_tail(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """使用 token 预算保护尾部消息。

        **尾部保护的设计理由：**

        1. 近因效应（Recency Effect）：
           最近的对话包含：
           - 当前任务状态和进度
           - 未完成的工具调用和待处理操作
           - 用户的最新反馈和修正
           - 模型的"思维链"和推理过程
           这些是模型的"工作记忆"，丢失后会导致对话断裂。

        2. 为什么用 token 预算而非固定条数？
           - 消息长度差异巨大：一条工具输出可能有 5000 tokens，而普通对话只有 50 tokens
           - 固定条数（如 20 条）可能导致：
             * 如果都是短消息：保护的内容太少，上下文不足
             * 如果包含长工具输出：保护的内容太多，挤占摘要空间
           - Token 预算确保尾部占用的上下文空间可控

        3. 预算计算公式：
           tail_tokens = threshold_tokens * summary_target_ratio
           - threshold_tokens: 触发压缩的阈值（如 context_length * 50%）
           - summary_target_ratio: 默认 0.20，即尾部预算占阈值的 20%
           - 例如：阈值 16000 tokens，尾部预算 = 16000 * 0.20 = 3200 tokens

        4. 从后向前遍历的原因：
           - 需要保护的是"最近"的消息，所以从列表末尾开始
           - 累加直到超过预算，确保尾部在预算范围内最大化

        Args:
            messages: 消息列表。

        Returns:
            尾部保护的消息列表（在 token 预算内的最近消息）。
        """
        # 计算尾部 token 预算：阈值 * 比例（默认 20%）
        # 这个预算与摘要预算共享同一个比例参数，因为两者竞争相同的 token 空间
        tail_tokens = int(self.threshold_tokens * self.summary_target_ratio)
        # 将 token 预算转换为字符限制（用于快速估算）
        tail_chars_limit = tail_tokens * CHARS_PER_TOKEN

        tail = []
        tail_chars = 0

        # 从后向前遍历（reversed），优先保护最近的消息
        for msg in reversed(messages):
            msg_chars = self._estimate_message_length(msg)
            # 如果加入当前消息会超出预算，停止
            # 注意：这里使用严格大于（>），确保预算不被突破
            if tail_chars + msg_chars > tail_chars_limit:
                break
            # insert(0, msg) 保持原始顺序（因为是从后向前遍历）
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

        **中间消息的定义：**
        中间消息 = 完整消息 - 头部保护 - 尾部保护

        这些是将被摘要化的消息，通常是：
        - 早期的工具调用和输出（已被剪枝）
        - 已完成的子任务和探索性对话
        - 过时的代码版本和中间思考

        **为什么中间消息可以被压缩？**
        - 头部已经保留了系统提示和初始意图
        - 尾部已经保留了当前工作状态
        - 中间部分的信息可以通过摘要提炼关键内容

        Args:
            messages: 完整消息列表。
            head: 头部保护消息。
            tail: 尾部保护消息。

        Returns:
            中间消息列表（需要被压缩的部分）。
        """
        head_count = len(head)
        tail_count = len(tail)
        # 中间部分的结束位置 = 总长度 - 尾部数量
        middle_end = len(messages) - tail_count

        # 切片：从头部之后到尾部之前
        # 边界情况：如果 head + tail >= messages，返回空列表（无需压缩）
        return messages[head_count:middle_end]

    def _calculate_summary_budget(self, compressed_chars: int) -> int:
        """计算摘要 token 预算。

        **预算计算公式：**
        ratio_budget = compressed_chars * SUMMARY_RATIO / CHARS_PER_TOKEN
        final_budget = max(MIN_SUMMARY_TOKENS, min(ratio_budget, SUMMARY_TOKENS_CEILING))

        **设计理由：**
        1. 比例预算（SUMMARY_RATIO = 0.20）：
           - 摘要长度与被压缩内容成正比
           - 20% 是经验值：既能保留关键信息，又不会占用过多上下文
           - 例如：压缩 10000 chars ≈ 2500 tokens，摘要预算 = 2500 * 0.20 = 500 tokens

        2. 下限保护（MIN_SUMMARY_TOKENS = 2000）：
           - 防止被压缩内容很少时，摘要过于简略
           - 2000 tokens 足够生成包含 Goal/Progress/Decisions 的结构化摘要
           - 即使只压缩了少量内容，也保持摘要的完整性

        3. 上限保护（SUMMARY_TOKENS_CEILING = 12000）：
           - 防止被压缩内容很大时，摘要占用过多上下文
           - 12000 tokens 约等于 48000 chars，已经是非常详细的摘要
           - 超过这个长度，摘要本身就成为了"新的长对话"，违背压缩初衷

        Args:
            compressed_chars: 压缩内容的字符数。

        Returns:
            摘要 token 预算（在 [MIN, MAX] 范围内）。
        """
        # 按比例计算预算：字符数 * 比例 / 每 token 字符数
        ratio_budget = int(compressed_chars * SUMMARY_RATIO / CHARS_PER_TOKEN)
        # 钳制到 [MIN_SUMMARY_TOKENS, SUMMARY_TOKENS_CEILING] 范围
        return max(MIN_SUMMARY_TOKENS, min(ratio_budget, SUMMARY_TOKENS_CEILING))

    def _generate_summary(
        self,
        messages: List[Dict[str, Any]],
        budget: int,
        model_caller: Callable | None = None,
    ) -> str:
        """生成结构化摘要。

        **摘要生成策略：**
        1. 构建提示：包含结构化模板和消息内容
        2. 调用主对话的 model_caller：复用主模型的凭证和客户端
        3. 失败降级：如果 LLM 调用失败，返回占位符而非抛出异常

        **为什么复用主对话的 model_caller？**
        - 简化架构：无需独立的辅助 LLM 客户端和凭证管理
        - 一致性：摘要使用与主对话相同的模型，保证理解能力
        - 可靠性：主对话凭证已验证可用，避免辅助客户端连接失败

        **为什么需要失败降级？**
        - 压缩是"优化"而非"必需"，摘要失败不应阻断对话
        - 占位符告知模型"摘要生成失败"，模型会更好地处理这种情况

        Args:
            messages: 中间消息列表。
            budget: 摘要 token 预算。
            model_caller: 主对话的模型调用函数。

        Returns:
            生成的摘要文本，或失败时的占位符。
        """
        # 构建摘要提示：包含结构化模板、预算和消息内容
        prompt = self._build_summary_prompt(messages, budget)

        # 调用主对话的 model_caller 生成摘要
        try:
            if model_caller is None:
                raise ValueError("model_caller is required for summary generation")

            summary_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a conversation summarizer. "
                        "Generate a concise, structured summary of the conversation. "
                        "Focus on key decisions, progress, and current state."
                    ),
                },
                {"role": "user", "content": prompt},
            ]

            response = model_caller(summary_messages, None)
            summary = response.get("content", "")
            if not summary:
                raise ValueError("Empty summary response")
        except Exception as e:
            # 失败降级：记录警告并返回占位符
            # 为什么不用空字符串？因为空字符串会让模型困惑"这里为什么是空的"
            # 占位符明确告知模型"摘要生成失败"，模型会更好地处理这种情况
            logger.warning(f"Summary generation failed: {e}")
            summary = "[Summary generation failed — middle context compacted without summary]"

        return summary

    def _build_summary_prompt(self, messages: List[Dict[str, Any]], budget: int) -> str:
        """构建摘要提示。

        **迭代摘要更新策略：**
        - 如果有前次摘要（_previous_summary），提示 LLM "更新"而非"重新生成"
        - 保留前次摘要的重要信息，添加新对话的细节
        - 优势：多次压缩后信息不会丢失，而是逐步精炼

        **结构化摘要模板：**
        - Goal: 对话的主要目标（帮助模型记住"为什么做"）
        - Progress: 完成了什么（帮助模型知道"做了什么"）
        - Key Decisions: 重要决策（帮助模型理解"为什么这样做"）
        - Modified Files: 修改过的文件（帮助模型追踪代码变更）
        - Next Steps: 下一步计划（帮助模型知道"接下来做什么"）

        这种结构化的好处：
        - 比自由文本更容易解析和检索
        - 强制 LLM 按类别组织信息，避免遗漏关键内容
        - 模型可以更快地定位需要的信息（如"上次修改了哪个文件"）

        Args:
            messages: 中间消息列表。
            budget: 摘要 token 预算。

        Returns:
            摘要提示文本。
        """
        # 检查是否有前次摘要，用于迭代更新
        if self._previous_summary:
            # 迭代更新模式：保留旧信息，添加新内容
            base_prompt = (
                f"Previous summary:\n{self._previous_summary}\n\n"
                f"Update the summary with new information from the following conversation. "
                f"Preserve important information from the previous summary and add new details.\n\n"
            )
        else:
            # 首次生成模式：从头生成摘要
            base_prompt = (
                "Summarize the following conversation. "
                "Focus on key decisions, progress, and current state.\n\n"
            )

        # 结构化摘要模板：强制 LLM 按类别组织信息
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

        # 将消息列表格式化为可读文本
        # 注意：这里只取 content 字段，忽略 tool_calls 等元数据
        # 因为摘要只需要知道"说了什么"，不需要知道"怎么调用的工具"
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

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        """估算消息列表的 token 数。

        使用简单的字符到 token 转换比例（1 token ≈ 4 chars）。
        这是一个粗略估算，用于预算追踪，不需要精确值。

        Args:
            messages: 消息列表。

        Returns:
            估算的 token 数。
        """
        total_chars = self._estimate_content_length(messages)
        return total_chars // CHARS_PER_TOKEN

    # =========================================================================
    # 预飞行和响应后压缩
    # =========================================================================

    def check_preflight(self, messages: List[Dict[str, Any]]) -> bool:
        """预飞行压缩检查。

        **预飞行检查的设计理由：**

        1. 什么时候触发？
           - 在进入主对话循环之前
           - 当恢复一个长会话时（--resume）
           - 当用户加载一个已有的 session 时

        2. 为什么需要预飞行检查？
           - 避免"一开始就失败"：如果加载的 session 已经接近上下文限制
             直接发送第一条消息就会触发 context_length_exceeded
           - 提前压缩可以确保 session 在安全范围内开始

        3. 与响应后检查的区别：
           - 预飞行：估算字符数，快速判断（无需 API 调用）
           - 响应后：使用 API 返回的实际 token 使用量

        Args:
            messages: 当前消息列表。

        Returns:
            True 如果需要压缩。
        """
        # 估算总字符数并转换为 tokens
        # 为什么用字符估算而非精确 token 计数？
        # - 预飞行检查需要快速，精确计数需要调用 tokenizer（较慢）
        # - 字符估算是足够好的启发式方法（误差约 ±10%）
        total_chars = self._estimate_content_length(messages)
        total_tokens = total_chars // CHARS_PER_TOKEN
        return total_tokens > self.threshold_tokens

    def check_post_response(self, response: Dict[str, Any]) -> bool:
        """响应后压缩检查。

        **响应后检查的触发条件：**

        1. context_length_exceeded 错误：
           - API 明确返回上下文超限错误
           - 这是"硬性"触发条件，必须立即压缩
           - 通常发生在估算不准确或消息突然变长时

        2. token 使用量超阈值：
           - API 返回的 usage.prompt_tokens 超过阈值
           - 这是"软性"触发条件，基于预设的百分比阈值
           - 允许在达到硬性限制之前主动压缩

        3. 为什么需要两种检查？
           - context_length_exceeded 是兜底：确保不会无限重试
           - token 阈值是优化：在达到限制之前主动管理上下文

        Args:
            response: API 响应。

        Returns:
            True 如果需要压缩。
        """
        # 检查 context_length_exceeded 错误
        # 这是 API 返回的硬性错误，表示上下文窗口已被完全填满
        error = response.get("error", {})
        if error.get("type") == "context_length_exceeded":
            return True

        # 检查 token 使用量
        # 使用 API 返回的实际 token 计数，比估算更准确
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        return prompt_tokens > self.threshold_tokens
