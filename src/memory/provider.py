"""MemoryProvider 抽象基类。

定义记忆提供者的标准接口，包含 17 个方法：
- 4 个核心抽象方法：name, is_available, initialize, system_prompt_block
- 4 个数据流方法（默认空实现）：prefetch, queue_prefetch, sync_turn, shutdown
- 5 个事件钩子（可选）：on_turn_start, on_session_end, on_pre_compress, on_delegation, on_memory_write
- 2 个工具接口：get_tool_schemas, handle_tool_call
- 2 个配置方法：get_config_schema, save_config
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class MemoryProvider(ABC):
    """记忆提供者抽象基类。

    子类必须实现 4 个核心抽象方法，其余方法有默认空实现可选择覆盖。
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称标识，如 'builtin', 'honcho', 'mem0' 等。"""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """检查提供者依赖是否满足（如 API Key、数据库连接等）。"""
        ...

    @abstractmethod
    def initialize(self, session_id: str, **kwargs) -> None:
        """会话初始化时调用，建立连接或加载状态。

        Args:
            session_id: 当前会话 ID。
            **kwargs: 可选参数（hermes_home, platform, agent_context 等）。
        """
        ...

    @abstractmethod
    def system_prompt_block(self) -> str:
        """返回注入到 system prompt 的记忆文本块。

        Returns:
            记忆上下文文本，空字符串表示无内容。
        """
        ...

    # =========================================================================
    # 数据流方法（默认空实现）
    # =========================================================================

    def prefetch(self, query: str, **kwargs) -> str:
        """主循环前，根据用户消息预取相关记忆。

        Args:
            query: 用户消息内容。
            **kwargs: 可选参数（session_id 等）。

        Returns:
            预取的记忆上下文文本。
        """
        return ""

    def queue_prefetch(self, query: str, **kwargs) -> None:
        """主循环后，为下一轮预取排队（后台异步）。

        Args:
            query: 用户消息内容。
            **kwargs: 可选参数（session_id 等）。
        """
        pass

    def sync_turn(self, user_content: str, assistant_content: str, **kwargs) -> None:
        """主循环后，将本轮对话同步到记忆存储。

        Args:
            user_content: 用户消息内容。
            assistant_content: 助手回复内容。
            **kwargs: 可选参数（session_id 等）。
        """
        pass

    def shutdown(self) -> None:
        """会话结束时调用，清理连接或保存状态。"""
        pass

    # =========================================================================
    # 事件钩子（可选）
    # =========================================================================

    def on_turn_start(self, turn: int, message: str, **kwargs) -> None:
        """每轮对话开始时调用。

        Args:
            turn: 当前轮次编号。
            message: 用户消息。
            **kwargs: 可选参数。
        """
        pass

    def on_session_end(self, messages: List[dict]) -> None:
        """会话结束时调用，用于最终记忆归档。

        Args:
            messages: 完整对话历史。
        """
        pass

    def on_pre_compress(self, messages: List[dict]) -> str:
        """上下文压缩前调用，在消息被丢弃前提取关键信息。

        Args:
            messages: 待压缩的对话历史。

        Returns:
            提取的关键信息文本。
        """
        return ""

    def on_delegation(self, task: str, result: str, **kwargs) -> None:
        """子代理完成任务时调用，观察子代理工作结果。

        Args:
            task: 委托任务描述。
            result: 任务执行结果。
            **kwargs: 可选参数（child_session_id 等）。
        """
        pass

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """内置记忆被修改时调用，镜像内置记忆的写入。

        当 Agent 通过内置 memory 工具修改 MEMORY.md/USER.md 时，
        外部 provider 收到此通知，可将变更纳入自己的用户模型。

        Args:
            action: 操作类型（'add', 'replace', 'remove'）。
            target: 目标类型（'memory', 'user'）。
            content: 写入的内容。
            metadata: 额外元数据。
        """
        pass

    # =========================================================================
    # 工具接口
    # =========================================================================

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """返回提供者定义的工具 schema 列表。

        Returns:
            OpenAI 函数调用格式的工具定义数组。
        """
        return []

    def handle_tool_call(self, tool_name: str, args: Dict[str, Any], **kwargs) -> str:
        """处理提供者定义的工具调用。

        Args:
            tool_name: 工具名称。
            args: 工具参数。
            **kwargs: 可选参数。

        Returns:
            工具执行结果（JSON 字符串）。

        Raises:
            NotImplementedError: 不支持该工具时抛出。
        """
        raise NotImplementedError(f"Provider {self.name} does not handle tool {tool_name}")

    # =========================================================================
    # 配置
    # =========================================================================

    def get_config_schema(self) -> List[Dict[str, Any]]:
        """返回提供者配置字段的 schema。

        Returns:
            配置字段定义数组。
        """
        return []

    def save_config(self, values: Dict[str, Any], hermes_home: str) -> None:
        """保存提供者配置。

        Args:
            values: 配置值字典。
            hermes_home: NanoHermes 主目录。
        """
        pass
