"""洞察/指标模块。

分析会话数据生成使用情况报告：
- Token 消耗聚合
- 成本估算
- 工具使用模式
- 活动趋势
"""

from src.insights.engine import (
    InsightsEngine,
    InsightsReport,
    TokenUsage,
    CostEstimate,
    estimate_cost,
    PRICING_DATABASE,
)

__all__ = [
    "InsightsEngine",
    "InsightsReport",
    "TokenUsage",
    "CostEstimate",
    "estimate_cost",
    "PRICING_DATABASE",
]
