"""上下文压缩模块。

可插拔的上下文管理系统，支持：
- ContextEngine 抽象基类（可插拔扩展点）
- ContextCompressor 分层压缩引擎（复用主对话 model_caller）
- CircuitBreaker 熔断器（防止压缩循环）
- BudgetTracker 预算追踪器（监控压缩效率）
- CompressionValidator 压缩验证器（评估压缩质量）
- CompressionMode 压缩模式（Reactive/Micro/Snip）
- 工具输出剪枝
- Session Splitting + parent_session_id 血缘链
"""

from src.compression.engine import ContextEngine
from src.compression.compressor import ContextCompressor
from src.compression.auxiliary import get_model_context_length
from src.compression.pruning import prune_tool_outputs, truncate_tool_call_args
from src.compression.feasibility import check_compression_model_feasibility
from src.compression.circuit_breaker import CircuitBreaker, CircuitState
from src.compression.budget_tracker import BudgetTracker, CompressionRecord
from src.compression.validator import CompressionValidator, ValidationResult
from src.compression.modes import (
    CompressionMode,
    BaseCompressionMode,
    ReactiveMode,
    MicroMode,
    SnipMode,
    create_mode,
)

__all__ = [
    "ContextEngine",
    "ContextCompressor",
    "get_model_context_length",
    "prune_tool_outputs",
    "truncate_tool_call_args",
    "check_compression_model_feasibility",
    # 新增组件
    "CircuitBreaker",
    "CircuitState",
    "BudgetTracker",
    "CompressionRecord",
    "CompressionValidator",
    "ValidationResult",
    "CompressionMode",
    "BaseCompressionMode",
    "ReactiveMode",
    "MicroMode",
    "SnipMode",
    "create_mode",
]
