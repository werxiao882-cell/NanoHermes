"""记忆系统模块。

可插拔的记忆后端系统，支持：
- MemoryStore 唯一数据源（§ 分隔符、文件锁、原子写入、漂移检测、冻结快照）
- MemoryProvider 抽象基类（14 个方法接口）
- MemoryManager 编排器（Fan-out 容错 + EventBus 集成）
- 内置文件记忆提供者（委托 MemoryStore）
"""

from src.memory.memory_store import MemoryStore
from src.memory.provider import MemoryProvider
from src.memory.manager import MemoryManager
from src.memory.file_provider import FileMemoryProvider

__all__ = [
    "MemoryStore",
    "MemoryProvider",
    "MemoryManager",
    "FileMemoryProvider",
]
