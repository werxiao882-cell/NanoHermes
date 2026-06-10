"""ConversationLoop - 核心对话循环。

循环流程：
1. 组装系统提示
2. 调用模型
3. 处理工具调用
4. 错误分类和重试
5. 后轮次钩子
6. 压缩触发检查

事件系统：
- 使用 EventBus 解耦循环逻辑与外部处理器
- 支持 15 种事件类型，覆盖完整生命周期
- 外部功能通过 loop.events.on() 订阅事件接入
- Debug 模式通过 DebugHandler 订阅事件实现，与核心循环完全解耦

动态工具管理：
- 支持 Tool Search 机制：启动时仅加载核心工具，其余通过搜索发现
- _discovered_tools 存储已发现的延迟加载工具 schema
- 每轮迭代合并 always_loaded + discovered 传递给模型
- search_tools 调用结果自动加入 discovered_tools
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

from src.conversation.error_classifier import ErrorClassifier, ErrorCategory
from src.conversation.events import EventBus, EventType

logger = logging.getLogger(__name__)


class ConversationLoop:
    """核心对话循环。

    管理模型调用、工具分发、重试、压缩触发的完整循环。
    通过 EventBus 与外部功能解耦。

    动态工具管理：
    - 维护 _always_loaded_schemas（始终可见的核心工具）
    - 维护 _discovered_tools（通过 search_tools 发现的工具）
    - 每轮合并两者传递给模型，实现按需加载

    Attributes:
        max_iterations: 最大迭代次数。
        events: 事件总线，用于订阅和触发事件。
    """

    def __init__(
        self,
        max_iterations: int = 90,
        model_call: Callable | None = None,
        tool_dispatch: Callable | None = None,
        debug: bool = False,
    ):
        """初始化对话循环。

        Args:
            max_iterations: 最大迭代次数。
            model_call: 模型调用函数。
            tool_dispatch: 工具分发函数。
            debug: 是否开启 debug 模式，注册 DebugHandler 输出详细日志。
        """
        self.max_iterations = max_iterations
        self._model_call = model_call
        self._tool_dispatch = tool_dispatch
        self._error_classifier = ErrorClassifier()
        self._interrupted = False
        self.events = EventBus()

        # 动态工具管理状态
        self._always_loaded_schemas: list[dict[str, Any]] = []
        self._discovered_tools: dict[str, dict[str, Any]] = {}

        # debug 模式：注册 DebugHandler 订阅事件输出调试日志
        if debug:
            from src.conversation.debug_handler import DebugHandler
            DebugHandler().register(self.events)

    def run(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """运行对话循环。

        Args:
            messages: 消息列表。
            tools: 工具 schema 列表（always loaded tools）。

        Returns:
            包含最终响应和元数据的字典。
        """
        # 初始化 always loaded schemas
        self._always_loaded_schemas = tools or []
        self._discovered_tools.clear()

        iteration = 0
        start_time = time.time()

        self.events.emit(EventType.LOOP_START, {
            "messages": messages,
            "tools": tools,
            "max_iterations": self.max_iterations,
        })

        while iteration < self.max_iterations:
            if self._interrupted:
                self.events.emit(EventType.INTERRUPT, {"iteration": iteration})
                break

            iteration += 1

            # 合并 always_loaded + discovered tools
            current_tools = self._get_current_tools()

            self.events.emit(EventType.ITERATION_START, {
                "iteration": iteration,
                "messages": messages,
            })

            # 调用模型
            model_start = time.time()
            try:
                self.events.emit(EventType.MODEL_REQUEST, {
                    "messages": messages,
                    "tools": current_tools,
                    "iteration": iteration,
                })
                response = self._call_model(messages, current_tools)
                model_elapsed = time.time() - model_start

                self.events.emit(EventType.MODEL_RESPONSE, {
                    "response": response,
                    "iteration": iteration,
                    "elapsed": model_elapsed,
                })
            except Exception as e:
                model_elapsed = time.time() - model_start
                classified = self._error_classifier.classify(
                    getattr(e, "status_code", None),
                    str(e),
                )
                self.events.emit(EventType.MODEL_ERROR, {
                    "error": e,
                    "classified": classified,
                    "iteration": iteration,
                    "elapsed": model_elapsed,
                })
                if classified.retryable and iteration < self.max_iterations:
                    logger.warning(f"可重试错误，重试中: {classified.message}")
                    self.events.emit(EventType.MODEL_RETRY, {
                        "error": e,
                        "attempt": iteration,
                        "iteration": iteration,
                    })
                    continue
                raise

            self.events.emit(EventType.ITERATION_END, {
                "iteration": iteration,
                "response": response,
            })

            # 检查是否有工具调用
            if response.get("tool_calls"):
                for tool_call in response["tool_calls"]:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name", "unknown")
                    tool_args = func.get("arguments", "{}")

                    tool_start = time.time()

                    self.events.emit(EventType.TOOL_START, {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "tool_call": tool_call,
                    })

                    try:
                        result = self._dispatch_tool(tool_call)
                    except Exception as e:
                        tool_elapsed = time.time() - tool_start
                        self.events.emit(EventType.TOOL_ERROR, {
                            "tool_name": tool_name,
                            "error": e,
                            "tool_call": tool_call,
                            "elapsed": tool_elapsed,
                        })
                        result = json.dumps({"error": str(e)})

                    # search_tools 调用：解析结果并添加到 discovered tools
                    if tool_name == "search_tools":
                        self._process_search_result(result)

                    tool_elapsed = time.time() - tool_start

                    self.events.emit(EventType.TOOL_END, {
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "result": result,
                        "elapsed": tool_elapsed,
                        "tool_call": tool_call,
                    })

                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    }
                    messages.append(tool_message)

                    self.events.emit(EventType.MESSAGE_APPEND, {
                        "message": tool_message,
                        "messages": messages,
                    })
                continue

            # 文本响应，结束循环
            total_elapsed = time.time() - start_time
            result = {
                "final_response": response.get("content", ""),
                "reasoning": response.get("reasoning"),
                "iterations": iteration,
                "usage": response.get("usage"),
                "raw_response": response.get("raw_response"),
            }

            self.events.emit(EventType.LOOP_END, {
                "result": result,
                "iterations": iteration,
                "total_elapsed": total_elapsed,
            })

            return result

        # 达到最大迭代
        total_elapsed = time.time() - start_time
        self.events.emit(EventType.MAX_ITERATIONS, {"iterations": iteration})

        result = {
            "final_response": "[达到最大迭代次数]",
            "reasoning": None,
            "iterations": iteration,
            "usage": None,
            "raw_response": None,
        }

        self.events.emit(EventType.LOOP_END, {
            "result": result,
            "iterations": iteration,
            "total_elapsed": total_elapsed,
        })

        return result

    # ========================================================================
    # 内部方法
    # ========================================================================

    def _get_current_tools(self) -> list[dict[str, Any]] | None:
        """获取当前轮次的工具集。

        合并 always_loaded + discovered tools，去重（discovered 覆盖 always_loaded）。

        Returns:
            合并后的工具 schema 列表。如果为空返回 None。
        """
        if not self._always_loaded_schemas and not self._discovered_tools:
            return None

        # 构建合并后的工具列表（discovered 覆盖 always_loaded）
        tool_map = {}
        for schema in self._always_loaded_schemas:
            tool_map[schema.get("name", "")] = schema
        for name, schema in self._discovered_tools.items():
            tool_map[name] = schema

        return list(tool_map.values())

    def _process_search_result(self, result: str) -> None:
        """处理 search_tools 调用结果，添加到 discovered tools。

        Args:
            result: search_tools 返回的 JSON 字符串。
        """
        try:
            schemas = json.loads(result)
            if isinstance(schemas, list):
                for schema in schemas:
                    if isinstance(schema, dict) and "name" in schema:
                        self._discovered_tools[schema["name"]] = schema
        except (json.JSONDecodeError, TypeError) as e:
            logger.debug(f"解析 search_tools 结果失败: {e}")

    def _call_model(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """调用模型。"""
        if self._model_call:
            return self._model_call(messages, tools)
        raise NotImplementedError("未设置 model_call 函数")

    def _dispatch_tool(self, tool_call: dict[str, Any]) -> str:
        """分发工具调用。"""
        if self._tool_dispatch:
            func = tool_call.get("function", {})
            return self._tool_dispatch(
                func.get("name", ""),
                func.get("arguments", {}),
            )
        return '{"error": "工具分发未实现"}'

    def interrupt(self) -> None:
        """中断对话循环。"""
        self._interrupted = True
