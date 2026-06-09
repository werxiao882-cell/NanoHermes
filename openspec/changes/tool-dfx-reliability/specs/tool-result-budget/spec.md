## ADDED Requirements

### Requirement: Tool result budget

系统 SHALL 实现 `apply_tool_result_budget(result: str, budget: int = 8000) -> str` 函数，对大型工具输出进行 token 级预算控制，防止单个工具结果占满上下文窗口。

参考 Claude Code 的工具结果管理:
- 工具输出可能非常大（如 `cat large_file.py`、`find / -type f`）
- 无限制注入会占满 LLM 上下文窗口
- 需要头尾保留截断策略，保留关键上下文

#### Scenario: 小结果不截断
- **WHEN** 工具输出 2000 tokens，预算 8000 tokens
- **THEN** 返回完整输出

#### Scenario: 大结果头尾保留截断
- **WHEN** 工具输出 15000 tokens，预算 8000 tokens
- **THEN** 保留头部 3500 tokens + 尾部 3500 tokens
- **AND** 中间替换为 `\n... [output truncated, ~8000 tokens omitted] ...\n`

#### Scenario: 每工具自定义预算
- **WHEN** `terminal` 工具声明 `max_result_tokens: 4000`
- **THEN** 使用 4000 而非全局 8000 作为预算

### Implementation Pseudo-Code

```python
"""src/tools/result_budget.py

工具结果预算管理。

设计参考: Claude Code 的工具结果管理机制:
  - 工具输出可能非常大（cat、find、ls -R 等命令）
  - 无限制注入会占满 LLM 上下文窗口
  - 头尾保留截断策略: 保留头部 + 尾部，中间用 ... 替换
  - 每工具可自定义预算覆盖

NanoHermes 适配:
  - 使用字符数估算 token 数（UTF-8 字符 ≈ token 的 0.7-1.0 倍）
  - 截断标记包含原始大小估算
  - 与 dispatcher.py 集成，在返回前强制执行
"""

from __future__ import annotations

import json
import math
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ─── 配置常量 ─────────────────────────────────────────────────
# 设计理由:
# - 默认 8000 tokens 足够大多数工具结果
# - terminal 工具输出通常更大，需要更严格的 4000 tokens
# - token 估算使用字符数 * 0.75（UTF-8 英文为主的经验值）

DEFAULT_RESULT_BUDGET_TOKENS = 8000
TERMINAL_RESULT_BUDGET_TOKENS = 4000
ENV_VAR_BUDGET = "NANOHERMES_TOOL_RESULT_BUDGET"
CHARS_PER_TOKEN = 0.75  # 字符到 token 的估算比例


def get_result_budget(tool_name: str, tool_budget: int | None = None) -> int:
    """获取工具结果预算（tokens）。

    优先级:
      1. 工具自定义预算 (tool_budget)
      2. 环境变量 NANOHERMES_TOOL_RESULT_BUDGET
      3. 工具类型默认值 (terminal → 4000, 其他 → 8000)

    Args:
        tool_name: 工具名称。
        tool_budget: 工具自定义预算（如有）。

    Returns:
        预算 token 数。
    """
    import os

    # 优先级 1: 工具自定义预算
    if tool_budget is not None and tool_budget > 0:
        return tool_budget

    # 优先级 2: 环境变量
    env_value = os.environ.get(ENV_VAR_BUDGET, "")
    if env_value:
        try:
            value = int(env_value)
            if value > 0:
                return value
        except ValueError:
            pass

    # 优先级 3: 工具类型默认值
    if tool_name == "terminal":
        return TERMINAL_RESULT_BUDGET_TOKENS
    return DEFAULT_RESULT_BUDGET_TOKENS


def estimate_tokens(text: str) -> int:
    """估算文本的 token 数。

    设计理由:
    - 精确 tokenization 需要调用 LLM tokenizer，开销较大
    - 对于截断目的，字符数 * 0.75 是足够准确的估算
    - Claude Code 也使用类似的字符数估算策略

    Args:
        text: 文本内容。

    Returns:
        估算的 token 数。
    """
    return math.ceil(len(text) * CHARS_PER_TOKEN)


def apply_tool_result_budget(
    result: str,
    budget: int = DEFAULT_RESULT_BUDGET_TOKENS,
    tool_name: str | None = None,
) -> str:
    """对工具结果应用预算截断。

    截断策略: 头尾保留，中间替换
      [头部 40%] ... [output truncated, N tokens omitted] ... [尾部 40%]

    为什么保留尾部？
      - 终端命令的错误信息通常在输出末尾
      - 文件列表的最后一行可能是总计信息
      - 日志的最后几行通常包含关键状态

    参考 Claude Code: applyToolResultBudget() 的头尾保留策略。

    Args:
        result: 工具执行结果。
        budget: 预算 token 数。
        tool_name: 工具名称（用于日志）。

    Returns:
        截断后的结果（如需要）。
    """
    # ── 步骤 1: 估算 token 数 ──
    result_tokens = estimate_tokens(result)

    # ── 步骤 2: 未超预算，直接返回 ──
    if result_tokens <= budget:
        return result

    # ── 步骤 3: 计算截断位置 ──
    # 预算的 80% 用于内容，20% 留给截断标记和余量
    usable_budget = int(budget * 0.8)
    head_ratio = 0.4  # 头部占 40%
    tail_ratio = 0.4  # 尾部占 40%
    # 剩余 20% 作为缓冲区

    head_chars = int(len(result) * head_ratio)
    tail_chars = int(len(result) * tail_ratio)

    # 调整: 确保头部 + 尾部不超过可用预算
    max_chars = int(usable_budget / CHARS_PER_TOKEN)
    if head_chars + tail_chars > max_chars:
        # 按比例缩减
        scale = max_chars / (head_chars + tail_chars)
        head_chars = int(head_chars * scale)
        tail_chars = int(tail_chars * scale)

    # ── 步骤 4: 截断 ──
    head = result[:head_chars]
    tail = result[-tail_chars:] if tail_chars > 0 else ""

    # 计算省略的 token 数
    omitted_tokens = result_tokens - estimate_tokens(head) - estimate_tokens(tail)

    # ── 步骤 5: 组装结果 ──
    tool_label = f" '{tool_name}'" if tool_name else ""
    truncated = (
        f"{head}"
        f"\n\n... [output{tool_label} truncated, "
        f"~{omitted_tokens} tokens / "
        f"{len(result) - head_chars - tail_chars} bytes omitted] ...\n\n"
        f"{tail}"
    )

    # ── 步骤 6: 记录日志 ──
    logger.info(
        f"工具结果{tool_label} 被截断: "
        f"{result_tokens} tokens → {estimate_tokens(truncated)} tokens "
        f"(预算: {budget} tokens, 省略: ~{omitted_tokens} tokens)"
    )

    return truncated


def apply_budget_to_dispatch_result(
    result: str,
    tool_name: str,
    tool_budget: int | None = None,
) -> str:
    """在 dispatch() 返回前应用结果预算。

    设计理由:
      - 统一入口点，确保所有工具结果都受预算控制
      - 自动跳过 JSON 错误结果（不包含大量数据）
      - 支持每工具自定义预算

    Args:
        result: dispatch() 的原始返回结果。
        tool_name: 工具名称。
        tool_budget: 工具自定义预算（如有）。

    Returns:
        应用预算后的结果。
    """
    # ── 跳过 JSON 错误结果 ──
    # 错误结果通常很短，不需要截断
    # 而且截断错误信息会影响调试
    try:
        data = json.loads(result)
        if "error" in data:
            return result
    except json.JSONDecodeError:
        pass  # 非 JSON 结果，继续处理

    # ── 获取预算 ──
    budget = get_result_budget(tool_name, tool_budget)

    # ── 应用截断 ──
    return apply_tool_result_budget(result, budget, tool_name)


# ─── 批量执行时的预算应用 ─────────────────────────────────────
# 参考 Claude Code: 批量工具执行时，每个工具结果独立应用预算


def apply_budget_to_batch_results(
    results: list[str],
    tool_names: list[str],
    tool_budgets: dict[str, int] | None = None,
) -> list[str]:
    """对批量工具结果逐个应用预算。

    设计理由:
      - 批量执行时，每个工具结果独立截断
      - 确保总上下文不超过模型窗口
      - 与 dispatch_batch() 集成

    Args:
        results: 工具结果列表。
        tool_names: 工具名称列表（与 results 一一对应）。
        tool_budgets: 每工具自定义预算映射。

    Returns:
        应用预算后的结果列表。
    """
    tool_budgets = tool_budgets or {}

    return [
        apply_budget_to_dispatch_result(
            result=result,
            tool_name=tool_name,
            tool_budget=tool_budgets.get(tool_name),
        )
        for result, tool_name in zip(results, tool_names)
    ]
```

### Requirement: Budget enforcement at dispatch level

工具结果预算 SHALL 在 `dispatch()` 和 `dispatch_batch()` 返回前强制执行。

#### Scenario: dispatch() 自动截断
- **WHEN** 工具返回 12000 tokens 的结果
- **THEN** `dispatch()` 截断至预算范围内
- **AND** 返回结果包含截断标记

#### Scenario: dispatch_batch() 逐个截断
- **WHEN** `dispatch_batch()` 执行 3 个工具，分别返回 2000/15000/3000 tokens
- **THEN** 第 2 个工具结果被截断，第 1、3 个保持完整

### Implementation Pseudo-Code (dispatch.py 集成)

```python
# 在 src/tools/dispatcher.py 中集成结果预算:

from src.tools.result_budget import apply_budget_to_dispatch_result

def dispatch(
    name: str,
    args: dict[str, Any] | str | None = None,
    task_id: str | None = None,
) -> str:
    """分发工具调用（现有逻辑不变）。"""
    # ... 现有查找、检查、执行逻辑 ...

    try:
        if entry.is_async:
            result = _async_bridge(entry.handler, call_args, task_id)
        else:
            result = entry.handler(**call_args, task_id=task_id)

        # ─── 新增: 应用结果预算 ───
        # 在返回前截断大型工具结果，防止占满上下文
        tool_budget = getattr(entry, 'max_result_tokens', None)
        result = apply_budget_to_dispatch_result(
            result=result,
            tool_name=name,
            tool_budget=tool_budget,
        )

        return result

    except Exception as e:
        # 错误结果不受预算控制（通常很短）
        logger.error(f"工具执行失败 '{name}': {e}", exc_info=True)
        return json.dumps({
            "error": f"工具执行失败: {type(e).__name__}: {e}"
        })
```
