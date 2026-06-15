"""后台审查模块。

在对话循环的后台 fork 一个 Agent 来评估对话内容，
决定是否应该保存记忆或更新技能。
使用工具白名单，不影响主对话循环。

公共 API：
- run_background_review(): 同步执行审查（供调度器 handler 调用）
- spawn_background_review(): 在后台线程中启动审查（独立使用）
- fork_agent(): 创建简化的子代理，支持工具调用循环

参考 ConversationLoop.run() 的工具调用模式实现。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# 后台审查使用的工具白名单
# 只允许审查 Agent 使用这些工具，避免影响主对话
REVIEW_TOOL_WHITELIST = {"memory", "skill_manage", "skill_view", "skills_list"}

# 最大迭代次数：防止无限循环
MAX_FORK_ITERATIONS = 5

# 记忆审查提示
MEMORY_REVIEW_PROMPT = """你是一个记忆审查助手。请分析以下对话内容，判断是否有值得保存的长期记忆。

如果发现有值得保存的信息（如用户偏好、重要事实、项目信息等），请使用 memory 工具保存。

对话内容：
{conversation}

请只保存真正重要的信息，避免保存临时性或上下文相关的信息。"""

# 技能审查提示
SKILL_REVIEW_PROMPT = """你是一个技能审查助手。请分析以下对话内容，判断是否有值得创建或更新技能的模式。

如果发现重复出现的工作流程、最佳实践或可复用的步骤，请使用 skill_manage 工具创建或更新技能。

对话内容：
{conversation}

技能应该是通用的、可复用的，而不是针对特定上下文的。"""

# 向后兼容（内部代码可能引用旧名称）
_MEMORY_REVIEW_PROMPT = MEMORY_REVIEW_PROMPT
_SKILL_REVIEW_PROMPT = SKILL_REVIEW_PROMPT


# ============================================================================
# 公共 API
# ============================================================================


def run_background_review(
    messages: list[dict[str, Any]],
    model_call: Callable,
    tool_dispatch: Callable,
    review_type: str = "memory",
    tool_schemas: list[dict[str, Any]] | None = None,
    tool_whitelist: set[str] | None = None,
    tool_dispatch_override: Callable | None = None,
    max_iterations: int = MAX_FORK_ITERATIONS,
) -> dict[str, Any]:
    """同步执行后台审查（供调度器 handler 直接调用）。

    这是后台审查的核心入口。封装了完整的审查流程：
    1. 截断消息（每条 500 字符）
    2. 格式化对话文本
    3. 构建审查提示（memory 或 skill）
    4. 调用 fork_agent() 执行工具调用循环

    调度器已经在后台线程中运行 handler，所以此函数是同步的，
    不再额外创建线程。

    Args:
        messages: 当前对话消息列表。
        model_call: 模型调用函数，签名 (messages, tools) -> response。
        tool_dispatch: 工具分发函数，签名 (name, args) -> result_str。
        review_type: 审查类型（"memory" 或 "skill"）。
        tool_schemas: 完整工具 schema 列表。
        tool_whitelist: 工具白名单（默认 REVIEW_TOOL_WHITELIST）。
        tool_dispatch_override: 自定义工具分发器（覆盖默认的 filtered_dispatch）。
            用于 memory 审查时将 memory 工具路由到 FileMemoryProvider。
        max_iterations: 最大迭代次数。

    Returns:
        审查结果字典，包含 final_response、iterations、review_type。
    """
    start_time = time.time()

    try:
        # 构建审查提示
        conversation_text = format_conversation(messages)
        prompt_template = MEMORY_REVIEW_PROMPT if review_type == "memory" else SKILL_REVIEW_PROMPT
        prompt = prompt_template.format(conversation=conversation_text)

        review_messages = [
            {"role": "system", "content": "你是一个专业的审查助手。"},
            {"role": "user", "content": prompt},
        ]

        # 确定工具分发器
        # 如果提供了 override，使用 override（如 memory 审查的路由分发器）
        # 否则使用默认的 tool_dispatch
        dispatch = tool_dispatch_override or tool_dispatch

        # 使用 fork_agent 进行审查（支持工具调用）
        result = fork_agent(
            messages=review_messages,
            model_call=model_call,
            tool_dispatch=dispatch,
            tool_whitelist=tool_whitelist,
            tool_schemas=tool_schemas,
            max_iterations=max_iterations,
        )

        elapsed = time.time() - start_time
        final = result.get("final_response", "")
        iters = result.get("iterations", 0)
        logger.info(
            f"后台{review_type}审查完成: {iters} 轮迭代, "
            f"耗时 {elapsed:.1f}s, "
            f"结果: {final[:100]}..."
        )

        return {
            **result,
            "review_type": review_type,
            "elapsed": elapsed,
        }

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"后台{review_type}审查失败 ({elapsed:.1f}s): {e}", exc_info=True)
        return {
            "final_response": "",
            "iterations": 0,
            "review_type": review_type,
            "elapsed": elapsed,
            "error": str(e),
        }


def spawn_background_review(
    messages: list[dict[str, Any]],
    model_call: Callable,
    tool_dispatch: Callable,
    review_type: str = "memory",
    tool_schemas: list[dict[str, Any]] | None = None,
) -> threading.Thread:
    """启动后台审查线程（独立使用，不依赖调度器）。

    在后台线程中调用 run_background_review()。
    适用于不通过 BackgroundTaskScheduler 的场景。

    Args:
        messages: 当前对话消息列表。
        model_call: 模型调用函数。
        tool_dispatch: 工具分发函数。
        review_type: 审查类型（"memory" 或 "skill"）。
        tool_schemas: 完整工具 schema 列表。

    Returns:
        后台审查线程。
    """

    def _review_task():
        run_background_review(
            messages=messages,
            model_call=model_call,
            tool_dispatch=tool_dispatch,
            review_type=review_type,
            tool_schemas=tool_schemas,
        )

    thread = threading.Thread(target=_review_task, daemon=True)
    thread.start()
    return thread


# ============================================================================
# 底层工具
# ============================================================================


def fork_agent(
    messages: list[dict[str, Any]],
    model_call: Callable,
    tool_dispatch: Callable,
    tool_whitelist: set[str] | None = None,
    tool_schemas: list[dict[str, Any]] | None = None,
    max_iterations: int = MAX_FORK_ITERATIONS,
) -> dict[str, Any]:
    """Fork 一个简化的 Agent 用于后台任务。

    参考 ConversationLoop.run() 的工具调用模式：
    1. 调用模型，传入过滤后的工具 schema
    2. 如果响应包含 tool_calls，逐个执行并追加结果
    3. 如果响应只有文本内容，返回最终结果
    4. 限制最大迭代次数防止无限循环

    Args:
        messages: 消息列表。
        model_call: 模型调用函数，签名 (messages, tools) -> response。
        tool_dispatch: 工具分发函数，签名 (name, args) -> result_str。
        tool_whitelist: 允许使用的工具白名单。
        tool_schemas: 完整工具 schema 列表，用于过滤后传给模型。
        max_iterations: 最大迭代次数。

    Returns:
        Agent 执行结果，包含 final_response 和 iterations。
    """
    whitelist = tool_whitelist or REVIEW_TOOL_WHITELIST

    # 过滤工具 schema：只保留白名单内的工具
    filtered_schemas = _filter_tool_schemas(tool_schemas, whitelist)

    # 创建过滤后的工具分发器
    def filtered_dispatch(name: str, args: dict[str, Any]) -> str:
        if name not in whitelist:
            return json.dumps({"error": f"Tool '{name}' not allowed in forked agent"})
        return tool_dispatch(name, args)

    current_messages = list(messages)
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        try:
            response = model_call(current_messages, filtered_schemas or None)
        except Exception as e:
            logger.error(f"fork_agent 模型调用失败 (iteration {iteration}): {e}")
            return {"final_response": "", "iterations": iteration, "error": str(e)}

        # 检查是否有工具调用（优先于内容检查）
        if response.get("tool_calls"):
            # 将 assistant 消息（含 tool_calls）追加到 messages
            assistant_message = {
                "role": "assistant",
                "content": response.get("content") or None,
                "tool_calls": response["tool_calls"],
            }
            current_messages.append(assistant_message)

            # 逐个处理工具调用
            for tool_call in response["tool_calls"]:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "unknown")
                tool_args_raw = func.get("arguments", "{}")

                # 解析参数
                if isinstance(tool_args_raw, str):
                    try:
                        tool_args = json.loads(tool_args_raw)
                    except json.JSONDecodeError:
                        tool_args = {"raw": tool_args_raw}
                elif isinstance(tool_args_raw, dict):
                    tool_args = tool_args_raw
                else:
                    tool_args = {}

                # 通过过滤分发器执行工具
                try:
                    result = filtered_dispatch(tool_name, tool_args)
                except Exception as e:
                    logger.warning(f"fork_agent 工具执行失败 [{tool_name}]: {e}")
                    result = json.dumps({"error": str(e)})

                # 追加工具结果消息
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", ""),
                    "content": result,
                }
                current_messages.append(tool_message)

            # 工具调用后继续迭代
            continue

        # 文本响应（无工具调用），结束循环
        content = response.get("content", "")
        return {
            "final_response": content,
            "iterations": iteration,
        }

    # 达到最大迭代次数
    logger.warning(f"fork_agent 达到迭代限制 ({max_iterations})")
    return {
        "final_response": "",
        "iterations": iteration,
        "warning": f"Reached iteration limit ({max_iterations})",
    }


def build_review_prompt(review_type: str, conversation: str) -> str:
    """构建审查提示。

    Args:
        review_type: 审查类型（"memory" 或 "skill"）。
        conversation: 格式化的对话内容。

    Returns:
        审查提示文本。
    """
    if review_type == "memory":
        return MEMORY_REVIEW_PROMPT.format(conversation=conversation)
    return SKILL_REVIEW_PROMPT.format(conversation=conversation)


def format_conversation(messages: list[dict[str, Any]], max_chars: int = 500) -> str:
    """格式化对话内容为文本。

    Args:
        messages: 消息列表。
        max_chars: 每条消息最大字符数。

    Returns:
        格式化的对话文本。
    """
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content:
            if len(content) > max_chars:
                content = content[:max_chars] + "..."
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


# 向后兼容
_format_conversation = format_conversation


# ============================================================================
# 内部工具
# ============================================================================


def _filter_tool_schemas(
    schemas: list[dict[str, Any]] | None,
    whitelist: set[str],
) -> list[dict[str, Any]]:
    """过滤工具 schema，只保留白名单内的工具。"""
    if not schemas:
        return []
    return [s for s in schemas if s.get("name", "") in whitelist]
