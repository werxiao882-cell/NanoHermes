"""上下文压缩模块。

对齐 hermes-agent-ref 的 ContextCompressor 实现，提供：
- 5 阶段压缩算法（修剪、边界、摘要、组装、清理）
- 结构化摘要模板
- Head/Tail 边界保护
- 辅助模型回退
- 会话分裂
"""

from src.compression.compressor import ContextCompressor

__all__ = ["ContextCompressor"]
