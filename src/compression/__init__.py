"""上下文压缩模块。

可插拔的上下文管理系统，支持：
- ContextEngine 抽象基类（可插拔扩展点）
- ContextCompressor 分层压缩引擎
- 辅助 LLM 客户端（后台任务，配置来自 nanohermes.json）
- 工具输出剪枝
- Session Splitting + parent_session_id 血缘链
"""

from src.compression.engine import ContextEngine
from src.compression.compressor import ContextCompressor
from src.compression.auxiliary import CompressionAuxiliaryClient, get_model_context_length
from src.compression.pruning import prune_tool_outputs, truncate_tool_call_args
from src.compression.feasibility import check_compression_model_feasibility

__all__ = [
    "ContextEngine",
    "ContextCompressor",
    "CompressionAuxiliaryClient",
    "get_model_context_length",
    "prune_tool_outputs",
    "truncate_tool_call_args",
    "check_compression_model_feasibility",
]
