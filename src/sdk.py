"""NanoHermes SDK - headless/programmatic usage interface.

核心职责：
提供 NanoHermesSDK 类，允许外部代码以编程方式与 NanoHermes 交互，
无需启动 TUI 界面。支持单轮对话、完整对话循环和流式响应。

设计理由：
- 复用现有模块（config loader, provider client, tool dispatcher, conversation loop），
  而非重新实现，保持行为一致性。
- SDK 初始化为"自动"模式：加载配置、创建客户端、初始化工具，一键就绪。
- 同时支持显式参数覆盖，方便测试和自定义部署。

使用示例：
    from src.sdk import NanoHermesSDK

    # 自动加载配置
    sdk = NanoHermesSDK()

    # 单轮对话
    response = sdk.chat("你好，请介绍一下自己")
    print(response)

    # 流式对话
    async for chunk in sdk.chat_stream("写一首诗"):
        print(chunk, end="", flush=True)

    # 完整对话（支持历史消息）
    result = await sdk.run_conversation([
        {"role": "user", "content": "你好"},
    ])
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, AsyncGenerator

from openai import OpenAI


class NanoHermesSDK:
    """NanoHermes 编程接口。

    自动初始化所有子模块，提供简化的对话 API。

    Attributes:
        config: 加载后的 Config 对象。
        model: 当前使用的模型名称。
        _model_call: 模型调用闭包（适配 ConversationLoop 接口）。
        _tool_dispatch: 工具分发函数。
        _tool_schemas: 初始工具 schema 列表（always loaded）。
        _system_prompt: 组装后的系统提示词。
        _debug: 是否开启 debug 模式。
    """

    def __init__(
        self,
        config_path: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        debug: bool = False,
    ):
        """初始化 SDK。

        设计理由：
        所有参数均为可选，不传时自动从配置系统加载。
        显式参数优先级高于配置文件，便于测试和自定义。

        Args:
            config_path: 配置文件路径（覆盖默认 nanohermes.json）。
            api_key: 显式 API Key（不写入配置，仅本次使用）。
            base_url: 显式 Base URL（用于自定义 API 端点）。
            model: 显式模型名称（覆盖配置中的模型）。
            debug: 是否开启 debug 模式，输出完整请求/响应 JSON。
        """
        # 配置日志（避免静默失败）
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        if debug:
            logging.getLogger("src").setLevel(logging.DEBUG)

        # ── 步骤 1: 加载配置 ──
        from src.config import load_config, get_api_key, get_base_url

        self.config = load_config(
            model=model,
            api_key=api_key,
            base_url=base_url,
            config_file=config_path,
        )
        resolved_api_key = get_api_key(self.config)
        resolved_base_url = get_base_url(self.config)
        self.model = self.config.model.name
        self._debug = debug

        if not resolved_api_key:
            raise ValueError("未找到 API Key，请检查 .env 文件或配置中的 api_key_env")

        # ── 步骤 2: 构建 Provider 客户端 ──
        client = OpenAI(api_key=resolved_api_key, base_url=resolved_base_url)
        from src.provider.openai_client import OpenAIClient as ProviderOpenAIClient

        provider_client = ProviderOpenAIClient(client, self.model, debug=debug)
        self._model_call = provider_client.build_caller()

        # ── 步骤 3: 初始化工具系统 ──
        from src.tools.registry import ToolRegistry, get_tool_schemas
        from src.tools.dispatcher import dispatch as tool_dispatch_func

        ToolRegistry.init_all_tools()
        self._tool_dispatch = tool_dispatch_func
        self._tool_schemas = get_tool_schemas(exclude_deferred=True)

        # ── 步骤 4: 组装系统提示词 ──
        from src.conversation.assembler import PromptAssembler

        assembler = PromptAssembler()
        from src.tools.registry import ToolRegistry as _TR

        tool_categories = _TR.get_tool_categories()
        system_prompt_result = assembler.build_system_prompt(
            model=self.model,
            skills=[],
            toolsets=list(tool_categories.keys()) if tool_categories else None,
            include_memory=False,
            include_user_profile=False,
        )
        self._system_prompt = system_prompt_result.full_text

    def chat(self, message: str) -> str:
        """发送单条消息，返回模型响应（同步）。

        设计理由：
        这是最常用的接口，适合简单的问答场景。
        内部创建临时消息列表和 ConversationLoop 执行一轮对话。

        Args:
            message: 用户消息文本。

        Returns:
            模型回复文本。
        """
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": message},
        ]
        result = asyncio.run(self._run_loop(messages))
        return result.get("final_response", "")

    async def run_conversation(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """运行完整对话循环（异步）。

        支持传入任意消息历史，SDK 自动添加系统提示词。
        适用于需要多轮对话、工具调用、上下文保持的场景。

        Args:
            messages: OpenAI 格式的消息列表（不含系统提示词，SDK 会自动添加）。

        Returns:
            包含 final_response, reasoning, iterations, usage 的字典。
        """
        full_messages = [
            {"role": "system", "content": self._system_prompt},
            *messages,
        ]
        return await self._run_loop(full_messages)

    async def chat_stream(self, message: str) -> AsyncGenerator[str, None]:
        """发送消息并流式接收响应。

        异步生成器，逐个 yield 增量文本片段。
        调用方可以使用 `async for` 消费流式输出。

        设计理由：
        - 使用 async generator 而非回调，保持调用链简洁。
        - 生成器天然支持背压（backpressure），调用方控制消费节奏。
        - 流式工具调用场景中，工具执行结果不作为流式文本 yield，
          仅在最终 response 中包含。

        Args:
            message: 用户消息文本。

        Yields:
            str: 增量文本片段。
        """
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": message},
        ]

        from src.config import get_api_key, get_base_url

        api_key = get_api_key(self.config)
        base_url = get_base_url(self.config)
        client = OpenAI(api_key=api_key, base_url=base_url)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if self._tool_schemas:
            kwargs["tools"] = [
                {"type": "function", "function": t} for t in self._tool_schemas
            ]

        # 流式调用主循环：支持工具调用
        for _iteration in range(90):  # 最大迭代次数，与 ConversationLoop 一致
            stream = client.chat.completions.create(**kwargs)

            full_content = ""
            reasoning = ""
            tool_calls_dict: dict[int, dict] = {}

            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # 提取增量文本并 yield
                if delta.content:
                    full_content += delta.content
                    yield delta.content

                # 提取 reasoning（不同提供商使用不同字段名）
                if hasattr(delta, "reasoning") and delta.reasoning:
                    reasoning += delta.reasoning
                elif hasattr(delta, "reasoning_content") and delta.reasoning_content:
                    reasoning += delta.reasoning_content

                # 提取工具调用：按 index 合并分片
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        tc_dict = tc.model_dump()
                        index = tc_dict.get("index", 0)
                        if index not in tool_calls_dict:
                            tool_calls_dict[index] = tc_dict
                        else:
                            existing = tool_calls_dict[index]
                            if tc_dict.get("id") and not existing.get("id"):
                                existing["id"] = tc_dict["id"]
                            if tc_dict.get("type"):
                                existing["type"] = tc_dict["type"]
                            func_new = tc_dict.get("function", {})
                            func_existing = existing.get("function", {})
                            if func_new.get("name"):
                                func_existing["name"] = func_new["name"]
                            if func_new.get("arguments"):
                                func_existing["arguments"] = func_existing.get("arguments", "") + func_new["arguments"]

                # 检查是否结束
                if chunk.choices[0].finish_reason:
                    break

            # 合并工具调用
            tool_calls = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())] if tool_calls_dict else []

            # 如果没有工具调用，结束
            if not tool_calls:
                return

            # 执行工具调用并添加到消息列表
            for tc in tool_calls:
                func_info = tc.get("function", {})
                tool_name = func_info.get("name", "")
                tool_args = func_info.get("arguments", "{}")

                tool_result = self._tool_dispatch(tool_name, tool_args)

                tool_message = {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": tool_result,
                }
                messages.append(tool_message)

                # search_tools 调用：解析结果并更新工具集
                if tool_name == "search_tools":
                    self._process_search_result_for_stream(tool_result)

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _run_loop(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """内部：运行 ConversationLoop（异步包装）。

        设计理由：
        ConversationLoop 是同步的，但 SDK 需要同时支持同步 chat() 和
        异步 run_conversation()。这里使用 asyncio.run() 在同步上下文中
        执行 loop.run()，并通过 asyncio.to_thread 包装以避免阻塞事件循环。

        Args:
            messages: 包含系统提示词的完整消息列表。

        Returns:
            对话结果字典。
        """
        from src.conversation.loop import ConversationLoop

        loop = ConversationLoop(
            model_call=self._model_call,
            tool_dispatch=self._tool_dispatch,
            debug=self._debug,
        )

        # ConversationLoop.run() 是同步方法，需要在事件循环中异步执行
        # 使用 to_thread 避免阻塞 asyncio 事件循环
        result = await asyncio.to_thread(loop.run, messages, self._tool_schemas)

        # 返回类型适配：chat() 只需字符串，run_conversation() 需要完整字典
        return result

    def _process_search_result_for_stream(self, result: str) -> None:
        """流式模式下处理 search_tools 结果。

        Args:
            result: search_tools 返回的 JSON 字符串。
        """
        import json
        try:
            schemas = json.loads(result)
            if isinstance(schemas, list):
                for schema in schemas:
                    if isinstance(schema, dict) and "name" in schema:
                        # 更新工具集（去重）
                        existing = {s.get("name") for s in self._tool_schemas}
                        if schema["name"] not in existing:
                            self._tool_schemas.append(schema)
        except (json.JSONDecodeError, TypeError):
            pass


def main_headless():
    """运行 headless REPL 交互模式。

    设计理由：
    提供一个简单的命令行 REPL，无需 TUI 即可与 NanoHermes 交互。
    适合管道脚本、CI/CD、SSH 远程等无图形环境。
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="NanoHermes - Headless REPL 模式")
    parser.add_argument("--debug", action="store_true", help="开启 debug 模式")
    parser.add_argument("--config", metavar="PATH", help="指定配置文件路径")
    parser.add_argument("--model", metavar="MODEL", help="指定模型名称")
    parser.add_argument("--api-key", metavar="KEY", help="指定 API Key")
    parser.add_argument("--base-url", metavar="URL", help="指定 Base URL")
    args = parser.parse_args()

    print("NanoHermes Headless REPL (Ctrl+D / Ctrl+C 退出)")
    print("=" * 50)

    try:
        sdk = NanoHermesSDK(
            config_path=args.config,
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            debug=args.debug,
        )
    except ValueError as e:
        print(f"[错误] {e}")
        sys.exit(1)

    print(f"模型: {sdk.model}")
    print(f"工具: {len(sdk._tool_schemas)} 个已加载")
    print("=" * 50)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        try:
            response = sdk.chat(user_input)
            print(f"\n{response}")
        except Exception as e:
            print(f"\n[错误] {type(e).__name__}: {e}")
