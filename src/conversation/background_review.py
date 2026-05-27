"""后台审查模块。

在对话循环的后台 fork 一个 Agent 来评估对话内容，
决定是否应该保存记忆或更新技能。
使用工具白名单，不影响主对话循环。
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

logger = logging.getLogger(__name__)

# 后台审查使用的工具白名单
# 只允许审查 Agent 使用这些工具，避免影响主对话
REVIEW_TOOL_WHITELIST = {"memory", "skill_manage", "skill_view", "skills_list"}

# 记忆审查提示
_MEMORY_REVIEW_PROMPT = """你是一个记忆审查助手。请分析以下对话内容，判断是否有值得保存的长期记忆。

如果发现有值得保存的信息（如用户偏好、重要事实、项目信息等），请使用 memory 工具保存。

对话内容：
{conversation}

请只保存真正重要的信息，避免保存临时性或上下文相关的信息。"""

# 技能审查提示
_SKILL_REVIEW_PROMPT = """你是一个技能审查助手。请分析以下对话内容，判断是否有值得创建或更新技能的模式。

如果发现重复出现的工作流程、最佳实践或可复用的步骤，请使用 skill_manage 工具创建或更新技能。

对话内容：
{conversation}

技能应该是通用的、可复用的，而不是针对特定上下文的。"""


def spawn_background_review(
    messages: list[dict[str, Any]],
    model_call: Callable,
    tool_dispatch: Callable,
    review_type: str = "memory",
) -> threading.Thread:
    """启动后台审查线程。

    Args:
        messages: 当前对话消息列表。
        model_call: 模型调用函数。
        tool_dispatch: 工具分发函数（会被过滤）。
        review_type: 审查类型（"memory" 或 "skill"）。

    Returns:
        后台审查线程。
    """

    def _review_task():
        """后台审查任务。"""
        try:
            # 构建审查提示
            conversation_text = _format_conversation(messages)
            if review_type == "memory":
                prompt = _MEMORY_REVIEW_PROMPT.format(conversation=conversation_text)
            else:
                prompt = _SKILL_REVIEW_PROMPT.format(conversation=conversation_text)

            # Fork 一个简化的 Agent 进行审查
            review_messages = [
                {"role": "system", "content": "你是一个专业的审查助手。"},
                {"role": "user", "content": prompt},
            ]

            # 调用模型进行审查
            response = model_call(review_messages, None)

            # 记录审查结果
            logger.info(f"后台{review_type}审查完成: {response.get('content', '')[:100]}...")

        except Exception as e:
            logger.error(f"后台审查失败: {e}")

    thread = threading.Thread(target=_review_task, daemon=True)
    thread.start()
    return thread


def fork_agent(
    messages: list[dict[str, Any]],
    model_call: Callable,
    tool_dispatch: Callable,
    tool_whitelist: set[str] | None = None,
) -> dict[str, Any]:
    """Fork 一个简化的 Agent 用于后台任务。

    Args:
        messages: 消息列表。
        model_call: 模型调用函数。
        tool_dispatch: 工具分发函数。
        tool_whitelist: 允许使用的工具白名单。

    Returns:
        Agent 执行结果。
    """
    whitelist = tool_whitelist or REVIEW_TOOL_WHITELIST

    # 创建过滤后的工具分发器
    def filtered_dispatch(name: str, args: dict[str, Any]) -> str:
        if name not in whitelist:
            return '{"error": "Tool not allowed in forked agent"}'
        return tool_dispatch(name, args)

    # 执行简化循环（最多 5 次迭代）
    current_messages = list(messages)
    for _ in range(5):
        response = model_call(current_messages, None)

        content = response.get("content", "")
        if content:
            return {"final_response": content, "iterations": 1}

    return {"final_response": "", "iterations": 0}


def build_review_prompt(review_type: str, conversation: str) -> str:
    """构建审查提示。

    Args:
        review_type: 审查类型（"memory" 或 "skill"）。
        conversation: 格式化的对话内容。

    Returns:
        审查提示文本。
    """
    if review_type == "memory":
        return _MEMORY_REVIEW_PROMPT.format(conversation=conversation)
    return _SKILL_REVIEW_PROMPT.format(conversation=conversation)


def _format_conversation(messages: list[dict[str, Any]]) -> str:
    """格式化对话内容为文本。

    Args:
        messages: 消息列表。

    Returns:
        格式化的对话文本。
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            # 限制每条消息的长度
            if len(content) > 500:
                content = content[:500] + "..."
            lines.append(f"{role}: {content}")
    return "\n".join(lines)
