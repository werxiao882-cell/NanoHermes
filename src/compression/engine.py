"""ContextEngine 抽象基类。

定义可插拔上下文引擎接口，包含 3 个核心抽象方法：
- update_from_response: 在每次模型响应后更新引擎内部状态
- should_compress: 判断当前上下文是否需要压缩
- compress: 执行实际的压缩操作

以及可选工具接口：
- get_tool_schemas: 返回引擎定义的工具 schema
- handle_tool_call: 处理引擎定义的工具调用
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ContextEngine(ABC):
    """可插拔上下文引擎抽象基类。

    第三方引擎（如 LCM、自定义摘要引擎）可替换内置压缩器，
    只需在配置中指定 context.engine。
    """

    @abstractmethod
    def update_from_response(self, response: Dict[str, Any]) -> None:
        """在每次模型响应后更新引擎内部状态。

        Args:
            response: 模型响应字典，包含 token 使用量等信息。
        """
        ...

    @abstractmethod
    def should_compress(self) -> bool:
        """判断当前上下文是否需要压缩。

        Returns:
            True 如果需要压缩，False 否则。
        """
        ...

    @abstractmethod
    def compress(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行实际的压缩操作。

        Args:
            messages: 当前对话消息列表。

        Returns:
            压缩结果字典，包含 keys:
                - messages: 压缩后的消息列表
                - summary: 生成的摘要文本
                - head_count: 头部保护消息数
                - tail_count: 尾部保护消息数
                - tail_messages: 尾部保护消息列表
        """
        ...

    # =========================================================================
    # 可选工具接口
    # =========================================================================

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回引擎定义的工具 schema（如 recall_context 工具）。

        Returns:
            OpenAI 函数调用格式的工具定义数组。
        """
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        """处理引擎定义的工具调用。

        Args:
            tool_name: 工具名称。
            args: 工具参数。

        Returns:
            工具执行结果（JSON 字符串）。

        Raises:
            NotImplementedError: 不支持该工具时抛出。
        """
        raise NotImplementedError(f"Engine does not handle tool {tool_name}")
