"""对话循环模块。

核心对话循环、错误分类、后台审查。

注意：后台审查功能已迁移到 src.background.review，此处保留向后兼容的导出。
"""

from src.conversation.loop import ConversationLoop
from src.conversation.error_classifier import ErrorClassifier, ClassifiedError

# 向后兼容：从新位置重新导出后台审查相关函数
from src.background.review import (
    run_background_review,
    spawn_background_review,
    fork_agent,
    build_review_prompt,
    format_conversation,
    REVIEW_TOOL_WHITELIST,
    MEMORY_REVIEW_PROMPT,
    SKILL_REVIEW_PROMPT,
)

__all__ = [
    "ConversationLoop",
    "ErrorClassifier",
    "ClassifiedError",
    # 向后兼容的后台审查导出
    "run_background_review",
    "spawn_background_review",
    "fork_agent",
    "build_review_prompt",
    "format_conversation",
    "REVIEW_TOOL_WHITELIST",
    "MEMORY_REVIEW_PROMPT",
    "SKILL_REVIEW_PROMPT",
]
