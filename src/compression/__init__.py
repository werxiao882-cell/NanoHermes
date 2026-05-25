"""上下文压缩模块。

辅助 LLM 自动压缩长对话：
- 检测上下文窗口使用率
- 生成结构化摘要
- 保护头部和尾部上下文
- 工具输出剪枝
"""

from src.compression.compressor import ContextCompressor

__all__ = ["ContextCompressor"]
