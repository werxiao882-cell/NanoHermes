"""工具输出剪枝。

在发送给 LLM 摘要器之前剪枝旧工具输出、截断长工具调用参数。
关键设计决策：工具调用参数截断必须保持 JSON 有效性。
"""

import json
from typing import Any, Dict, List

# 工具输出剪枝阈值（字符数）
TOOL_OUTPUT_PRUNE_THRESHOLD = 200
TOOL_OUTPUT_PRUNE_PLACEHOLDER = "[Tool result pruned — original too large]"

# 工具调用参数截断阈值（字符数）
TOOL_CALL_ARGS_TRUNCATE_THRESHOLD = 200


def prune_tool_outputs(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """剪枝旧工具输出。

    将超过阈值的工具输出替换为占位符文本。
    这是最廉价的压缩步骤，不需要 LLM 调用。

    Args:
        messages: 消息列表。

    Returns:
        剪枝后的消息列表。
    """
    pruned = []
    for msg in messages:
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > TOOL_OUTPUT_PRUNE_THRESHOLD:
                msg = {**msg, "content": TOOL_OUTPUT_PRUNE_PLACEHOLDER}
        pruned.append(msg)
    return pruned


def truncate_tool_call_args(args_json: str, max_chars: int = TOOL_CALL_ARGS_TRUNCATE_THRESHOLD) -> str:
    """截断工具调用参数，保持 JSON 有效性。

    关键设计决策：早期实现直接切片原始 JSON 字符串，导致未终止的字符串
    和缺失的闭合括号，使 MiniMax 等提供商返回 400 错误。
    新实现解析 JSON，截断字符串叶子节点，重新序列化。

    Args:
        args_json: 工具调用参数 JSON 字符串。
        max_chars: 字符串最大字符数。

    Returns:
        截断后的 JSON 字符串，保持结构有效。
    """
    try:
        parsed = json.loads(args_json)
        truncated = _truncate_object_strings(parsed, max_chars)
        return json.dumps(truncated, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        # 不是有效 JSON，返回原始字符串
        return args_json


def _truncate_object_strings(obj: Any, max_chars: int) -> Any:
    """递归截断对象中的字符串叶子节点。

    Args:
        obj: 要处理的对象。
        max_chars: 字符串最大字符数。

    Returns:
        截断后的对象。
    """
    if isinstance(obj, str):
        if len(obj) > max_chars:
            return obj[:max_chars] + "...[truncated]"
        return obj
    elif isinstance(obj, list):
        return [_truncate_object_strings(item, max_chars) for item in obj]
    elif isinstance(obj, dict):
        return {k: _truncate_object_strings(v, max_chars) for k, v in obj.items()}
    return obj
