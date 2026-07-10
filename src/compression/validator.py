"""压缩验证器实现。

评估压缩质量，包括信息保留度、摘要长度和关键信息完整性。

设计理由：
- 压缩后需要验证质量，避免过度压缩导致信息丢失
- 使用轻量级关键词匹配（Jaccard 相似度）评估信息保留度
- 检查摘要长度是否在合理范围内
- 验证关键信息（文件变更、用户意图、工具调用）是否保留
- 验证失败时提供警告信息，帮助调试和优化
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


# 停用词列表（中英文）
# 设计理由：停用词对信息保留度计算无意义，需要过滤
STOP_WORDS: Set[str] = {
    # 英文停用词
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no",
    "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "just", "because", "but", "and", "or", "if", "while", "although",
    "this", "that", "these", "those", "i", "me", "my", "myself", "we",
    "our", "ours", "ourselves", "you", "your", "yours", "yourself",
    "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs",
    "themselves", "what", "which", "who", "whom",
    # 中文停用词
    "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一",
    "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着",
    "没有", "看", "好", "自己", "这", "他", "她", "它", "们", "那", "些",
    "什么", "怎么", "为什么", "哪", "谁", "多少", "几", "吗", "呢", "吧",
    "啊", "哦", "嗯", "哈", "呀", "啦", "哇", "嘛", "喔", "噢",
}

# 文件变更关键词
FILE_CHANGE_KEYWORDS: Set[str] = {
    "file", "文件", "create", "创建", "modify", "修改", "delete", "删除",
    "write", "写入", "read", "读取", "update", "更新", "save", "保存",
    "path", "路径", "directory", "目录", "folder", "文件夹",
}

# 工具调用关键词
TOOL_CALL_KEYWORDS: Set[str] = {
    "tool", "工具", "function", "函数", "call", "调用", "execute", "执行",
    "run", "运行", "invoke", "调用", "api", "接口",
}


@dataclass
class ValidationResult:
    """验证结果数据类。

    Attributes:
        is_valid: 验证是否通过。
        retention_rate: 信息保留率（0.0 ~ 1.0）。
        summary_length: 摘要长度（字符数）。
        has_file_changes: 是否包含文件变更信息。
        has_user_intent: 是否包含用户意图。
        has_tool_calls: 是否包含工具调用信息。
        warnings: 警告信息列表。
    """
    is_valid: bool
    retention_rate: float
    summary_length: int
    has_file_changes: bool
    has_user_intent: bool
    has_tool_calls: bool
    warnings: List[str] = field(default_factory=list)


class CompressionValidator:
    """压缩验证器，用于评估压缩质量。

    验证维度：
    1. 信息保留度：原始消息和摘要的关键词 Jaccard 相似度
    2. 摘要长度：是否在合理范围内（min ~ max 字符）
    3. 关键信息完整性：文件变更、用户意图、工具调用

    设计理由：
    - min_retention_rate 默认 0.6：保留 60% 的关键词，平衡压缩率和信息完整性
    - min_summary_length 默认 500：避免过度压缩导致信息丢失
    - max_summary_length 默认 12000：避免摘要过长，失去压缩意义
    """

    def __init__(
        self,
        min_retention_rate: float = 0.6,
        min_summary_length: int = 500,
        max_summary_length: int = 12000,
    ):
        """初始化压缩验证器。

        Args:
            min_retention_rate: 最小信息保留率（0.0 ~ 1.0）。
            min_summary_length: 最小摘要长度（字符数）。
            max_summary_length: 最大摘要长度（字符数）。
        """
        if not 0.0 <= min_retention_rate <= 1.0:
            raise ValueError(
                f"min_retention_rate must be between 0.0 and 1.0, got {min_retention_rate}"
            )
        if min_summary_length < 0:
            raise ValueError(
                f"min_summary_length must be non-negative, got {min_summary_length}"
            )
        if max_summary_length < min_summary_length:
            raise ValueError(
                f"max_summary_length must be >= min_summary_length, "
                f"got {max_summary_length} < {min_summary_length}"
            )

        self._min_retention_rate = min_retention_rate
        self._min_summary_length = min_summary_length
        self._max_summary_length = max_summary_length

    def extract_keywords(self, text: str) -> Set[str]:
        """提取文本中的关键词。

        处理逻辑：
        1. 转换为小写
        2. 使用正则表达式提取单词（中英文）
        3. 过滤停用词
        4. 过滤长度 < 2 的词

        Args:
            text: 输入文本。

        Returns:
            关键词集合。
        """
        if not text:
            return set()

        # 转换为小写
        text_lower = text.lower()

        # 提取单词（支持中英文）
        # 英文：字母、数字、下划线
        # 中文：Unicode 中文字符
        words = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text_lower)

        # 过滤停用词和短词
        keywords = {
            word for word in words
            if word not in STOP_WORDS and len(word) >= 2
        }

        return keywords

    def calculate_retention_rate(
        self,
        original_messages: List[Dict[str, Any]],
        summary: str,
        compressed_source: List[Dict[str, Any]] | None = None,
    ) -> float:
        """计算信息保留率。

        使用 Jaccard 相似度：|A ∩ B| / |A ∪ B|

        设计理由：
        摘要是针对"被压缩的中间消息"生成的，而非全部原始消息。
        头尾保护的消息未被压缩，不应计入保留率计算的分母。
        如果提供了 compressed_source（实际被压缩的消息），直接用它计算。
        否则使用启发式：取原始消息中间 60% 作为近似。

        Args:
            original_messages: 原始消息列表。
            summary: 压缩后的摘要。
            compressed_source: 实际被压缩的中间消息（可选）。

        Returns:
            信息保留率（0.0 ~ 1.0）。
        """
        # 提取摘要的关键词
        summary_keywords = self.extract_keywords(summary)

        # 优先使用实际被压缩的消息
        if compressed_source:
            source_messages = compressed_source
        else:
            # 启发式：只取中间 60% 的消息作为基准
            n = len(original_messages)
            if n > 10:
                skip = int(n * 0.2)
                source_messages = original_messages[skip:n - skip]
            else:
                source_messages = original_messages

        original_text = " ".join(
            msg.get("content", "") for msg in source_messages
            if isinstance(msg.get("content"), str)
        )
        original_keywords = self.extract_keywords(original_text)

        # 计算 Jaccard 相似度
        if not original_keywords:
            return 1.0 if not summary_keywords else 0.0

        intersection = original_keywords & summary_keywords
        union = original_keywords | summary_keywords

        if not union:
            return 1.0

        return len(intersection) / len(union)

    def validate_summary_length(self, summary: str) -> tuple[bool, List[str]]:
        """验证摘要长度。

        Args:
            summary: 摘要文本。

        Returns:
            (is_valid, warnings) 元组。
        """
        length = len(summary)
        warnings = []

        if length < self._min_summary_length:
            warnings.append(
                f"Summary too short: {length} chars < {self._min_summary_length} chars"
            )
            return False, warnings

        if length > self._max_summary_length:
            warnings.append(
                f"Summary too long: {length} chars > {self._max_summary_length} chars"
            )
            return False, warnings

        return True, warnings

    def check_key_information(
        self,
        original_messages: List[Dict[str, Any]],
        compressed_messages: List[Dict[str, Any]],
        summary: str,
    ) -> Dict[str, bool]:
        """检查关键信息完整性。

        检查维度：
        1. 文件变更信息：原始消息包含文件操作，摘要是否提及
        2. 用户意图：压缩后消息的最后 5 条是否包含用户消息
        3. 工具调用信息：原始消息包含工具调用，摘要是否提及

        Args:
            original_messages: 原始消息列表。
            compressed_messages: 压缩后的消息列表。
            summary: 摘要文本。

        Returns:
            包含 has_file_changes、has_user_intent、has_tool_calls 的字典。
        """
        summary_lower = summary.lower()
        summary_keywords = self.extract_keywords(summary_lower)

        # 检查文件变更信息
        original_text = " ".join(
            msg.get("content", "") for msg in original_messages
            if isinstance(msg.get("content"), str)
        )
        original_lower = original_text.lower()
        has_file_ops = any(kw in original_lower for kw in FILE_CHANGE_KEYWORDS)
        has_file_changes = has_file_ops and any(
            kw in summary_keywords for kw in FILE_CHANGE_KEYWORDS
        )

        # 检查用户意图（最后 5 条消息是否包含用户消息）
        recent_messages = compressed_messages[-5:]
        has_user_intent = any(
            msg.get("role") == "user" for msg in recent_messages
        )

        # 检查工具调用信息
        has_tool_ops = "tool_calls" in original_text.lower() or any(
            "tool_calls" in msg for msg in original_messages
        )
        has_tool_calls = has_tool_ops and any(
            kw in summary_keywords for kw in TOOL_CALL_KEYWORDS
        )

        return {
            "has_file_changes": has_file_changes,
            "has_user_intent": has_user_intent,
            "has_tool_calls": has_tool_calls,
        }

    def validate(
        self,
        original_messages: List[Dict[str, Any]],
        compressed_messages: List[Dict[str, Any]],
        summary: str,
        compressed_source: List[Dict[str, Any]] | None = None,
    ) -> ValidationResult:
        """验证压缩质量。

        验证流程：
        1. 计算信息保留率
        2. 验证摘要长度
        3. 检查关键信息完整性
        4. 综合判断是否通过

        Args:
            original_messages: 原始消息列表（全部）。
            compressed_messages: 压缩后的消息列表。
            summary: 摘要文本。
            compressed_source: 实际被压缩的中间消息（用于保留率计算）。
                            如果不传，则使用启发式估算。

        Returns:
            验证结果。
        """
        warnings = []

        # 1. 计算信息保留率
        retention_rate = self.calculate_retention_rate(
            original_messages, summary, compressed_source
        )
        if retention_rate < self._min_retention_rate:
            warnings.append(
                f"Low information retention: {retention_rate:.2f} < {self._min_retention_rate:.2f}"
            )

        # 2. 验证摘要长度
        length_valid, length_warnings = self.validate_summary_length(summary)
        warnings.extend(length_warnings)

        # 3. 检查关键信息完整性
        key_info = self.check_key_information(
            original_messages, compressed_messages, summary
        )

        # 4. 综合判断
        is_valid = (
            retention_rate >= self._min_retention_rate
            and length_valid
        )

        return ValidationResult(
            is_valid=is_valid,
            retention_rate=retention_rate,
            summary_length=len(summary),
            has_file_changes=key_info["has_file_changes"],
            has_user_intent=key_info["has_user_intent"],
            has_tool_calls=key_info["has_tool_calls"],
            warnings=warnings,
        )
