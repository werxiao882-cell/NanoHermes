"""task-notification 格式化。

子 Agent 完成后，将结果作为结构化 XML 消息回流到主 Agent 上下文。
参考 Claude Code 的 task-notification 格式。

设计理由：
- XML 格式让主 Agent 能识别这是系统通知而非用户消息
- 包含 task_id、status、summary 等关键信息
- 作为 user role 消息注入到主对话的 messages 列表中
"""

from __future__ import annotations


def format_task_notification(
    task_id: str,
    status: str,
    summary: str,
    tool_calls: int = 0,
    duration_s: float = 0,
) -> str:
    """格式化 task-notification XML 消息。

    Args:
        task_id: 任务唯一 ID。
        status: 任务状态（completed/failed/timeout）。
        summary: 任务结果摘要。
        tool_calls: 工具调用次数。
        duration_s: 耗时（秒）。

    Returns:
        XML 格式的 task-notification 字符串。
    """
    return (
        f"<task-notification>\n"
        f"<task-id>{task_id}</task-id>\n"
        f"<status>{status}</status>\n"
        f"<summary>{summary}</summary>\n"
        f"<tool-calls>{tool_calls}</tool-calls>\n"
        f"<duration>{duration_s:.1f}s</duration>\n"
        f"</task-notification>"
    )
