"""记忆系统模块。

可插拔的记忆后端系统，支持：
- MemoryStore 唯一数据源（§ 分隔符、文件锁、原子写入、漂移检测、冻结快照）
- MemoryProvider 抽象基类（17 个方法接口）
- MemoryManager 编排器（Fan-out 容错）
- 内置文件记忆提供者（委托 MemoryStore）
- 上下文隔离和流式清洗
- MemoryEventHandler（订阅 Loop 事件总线）
"""

from src.memory.memory_store import MemoryStore
from src.memory.provider import MemoryProvider
from src.memory.manager import MemoryManager
from src.memory.file_provider import FileMemoryProvider
from src.memory.context_fencing import sanitize_context, StreamingContextScrubber
from src.memory.event_handler import MemoryEventHandler

__all__ = [
    "MemoryStore",
    "MemoryProvider",
    "MemoryManager",
    "FileMemoryProvider",
    "sanitize_context",
    "StreamingContextScrubber",
    "MemoryEventHandler",
]
