"""Streaming CLI - Claude Code 风格的终端界面。

特性：
- 真正的流式输出（OpenAI SDK streaming API）
- 工具调用内联显示
- 彩色输出（ANSI）
- 干净的提示符设计
- 思考内容显示
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Generator

# ============================================================================
# ANSI 颜色代码
# ============================================================================
class Colors:
    """ANSI 终端颜色代码。"""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    GRAY = "\033[90m"


def _color(text: str, c: str) -> str:
    return f"{c}{text}{Colors.RESET}"


def _dim(text: str) -> str:
    return f"{Colors.DIM}{text}{Colors.RESET}"


def _bold(text: str) -> str:
    return f"{Colors.BOLD}{text}{Colors.RESET}"


# ============================================================================
# 流式输出
# ============================================================================
def stream_text(text: str, delay: float = 0.01) -> None:
    """逐字符流式打印文本。

    Args:
        text: 要打印的文本。
        delay: 每个字符的延迟（秒）。
    """
    for char in text:
        print(char, end="", flush=True)
        if delay > 0:
            time.sleep(delay)
    print()


# ============================================================================
# 工具调用显示
# ============================================================================
def print_tool_call(name: str, args_str: str) -> None:
    """打印工具调用信息。"""
    print()
    print(f"  {_color('⚡', Colors.CYAN)} {_bold(name)}")
    # 缩进显示参数
    try:
        args = json.loads(args_str)
        args_formatted = json.dumps(args, ensure_ascii=False, indent=2)
    except json.JSONDecodeError:
        args_formatted = args_str

    for line in args_formatted.split("\n"):
        print(f"    {_dim(line)}")
    print()


def print_tool_result(name: str, result: str) -> None:
    """打印工具执行结果。"""
    # 截断长结果
    if len(result) > 200:
        result = result[:200] + _dim("...")

    print(f"  {_color('✓', Colors.GREEN)} {_bold(name)}")
    for line in result.split("\n")[:5]:
        print(f"    {_dim(line)}")
    print()


# ============================================================================
# 思考内容显示
# ============================================================================
def print_thinking(reasoning: str) -> None:
    """打印思考内容（折叠显示）。"""
    if not reasoning:
        return

    # 折叠：只显示前 60 字符
    preview = reasoning[:60] + "..." if len(reasoning) > 60 else reasoning
    print(_dim(f"  💭 {preview}"))


# ============================================================================
# 提示符
# ============================================================================
def print_prompt() -> None:
    """打印输入提示符。"""
    print()
    sys.stdout.write(f"  {_color('❯', Colors.GREEN)} ")
    sys.stdout.flush()


def print_banner(model: str) -> None:
    """打印启动横幅。"""
    print()
    print(f"  {_bold(_color('NanoHermes', Colors.CYAN))} {_dim('v0.1.0')}")
    print(f"  {_dim('Model: ' + model)}")
    print(f"  {_dim('Type quit to exit, clear to clear history')}")
    print(f"  {_dim('─' * 50)}")


# ============================================================================
# 主循环
# ============================================================================
def run_streaming_cli(
    client,
    model: str,
    tool_schemas: list[dict[str, Any]] | None = None,
    dispatch: Any = None,
    debug: bool = False,
) -> None:
    """运行流式 CLI 主循环。

    Args:
        client: OpenAI SDK 客户端实例。
        model: 模型名称。
        tool_schemas: 工具 schema 列表。
        dispatch: 工具分发函数。
        debug: 是否开启 debug 模式。
    """
    print_banner(model)

    messages = [
        {"role": "system", "content": "你是 NanoHermes，一个有用的 AI 助手。"},
    ]

    while True:
        print_prompt()

        try:
            user_input = input()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{_dim('  Goodbye!')}")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print(_dim("  Goodbye!"))
            break

        if user_input.lower() == "clear":
            messages = [messages[0]]
            print(_dim("  History cleared."))
            continue

        # 添加用户消息
        messages.append({"role": "user", "content": user_input})

        # Debug: 打印请求
        if debug:
            print(f"\n{_dim('  [DEBUG] Request:')}")
            print(_dim(json.dumps(messages[-2:], ensure_ascii=False, indent=2)))

        try:
            # 调用模型（流式）
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            if tool_schemas:
                kwargs["tools"] = tool_schemas

            stream = client.chat.completions.create(**kwargs)

            # 处理流式响应
            full_content = ""
            tool_calls = {}
            reasoning = ""

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if not delta:
                    continue

                # 提取 reasoning
                if hasattr(delta, 'reasoning') and delta.reasoning:
                    reasoning += delta.reasoning
                elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    reasoning += delta.reasoning_content

                # 提取工具调用
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls:
                            tool_calls[idx] = {"id": tc.id, "name": "", "arguments": ""}
                        if tc.function:
                            if tc.function.name:
                                tool_calls[idx]["name"] = tc.function.name
                            if tc.function.arguments:
                                tool_calls[idx]["arguments"] += tc.function.arguments

                # 提取文本内容
                if delta.content:
                    if not full_content:
                        print()  # 首次输出前换行
                    print(delta.content, end="", flush=True)
                    full_content += delta.content

            # 打印 reasoning
            if reasoning:
                print_thinking(reasoning)

            # 打印完成
            print()

            # Debug: 打印响应
            if debug:
                print(f"\n{_dim('  [DEBUG] Response:')}")
                print(_dim(f"  Content: {full_content[:200]}..."))
                if tool_calls:
                    for tc in tool_calls.values():
                        print(_dim(f"  Tool: {tc['name']}({tc['arguments'][:100]})"))

            # 处理工具调用
            if tool_calls:
                # 添加 assistant 消息
                assistant_msg = {"role": "assistant", "content": full_content}
                if tool_calls:
                    assistant_msg["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            },
                        }
                        for tc in tool_calls.values()
                    ]
                messages.append(assistant_msg)

                # 执行工具
                if dispatch:
                    for tc in tool_calls.values():
                        print_tool_call(tc["name"], tc["arguments"])
                        result = dispatch(tc["name"], tc["arguments"])
                        print_tool_result(tc["name"], result)

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc["id"],
                            "content": result,
                        })

                    # 继续调用模型（处理工具结果）
                    kwargs["messages"] = messages
                    stream2 = client.chat.completions.create(**kwargs)

                    full_content2 = ""
                    for chunk in stream2:
                        delta = chunk.choices[0].delta if chunk.choices else None
                        if delta and delta.content:
                            print(delta.content, end="", flush=True)
                            full_content2 += delta.content
                    print()
                    full_content = full_content2

            # 添加 assistant 消息
            messages.append({"role": "assistant", "content": full_content})

        except Exception as e:
            print(f"\n{_color(f'  Error: {e}', Colors.RED)}")
