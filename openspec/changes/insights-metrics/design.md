## 上下文

业界成熟的自进化 AI Agent 系统的洞察引擎模块 (~930 LOC) 实现了完整的洞察引擎。核心设计决策包括：
- 直接查询 SessionDB 生成报告
- 成本估算基于模型定价数据
- 工具使用模式从消息中提取
- 每日活动趋势计算
- 终端条形图可视化

## 技术方案

### 1. InsightsEngine

```typescript
export class InsightsEngine {
  constructor(private db: SessionDB) {}
  
  generate(days: number = 30, source?: string): InsightsReport {
    const cutoff = Date.now() - (days * 86400 * 1000);
    
    // 收集原始数据
    const sessions = this.getSessions(cutoff, source);
    const toolUsage = this.getToolUsage(cutoff, source);
    const skillUsage = this.getSkillUsage(cutoff, source);
    const messageStats = this.getMessageStats(cutoff, source);
    
    if (sessions.length === 0) {
      return this.emptyReport(days, source);
    }
    
    return {
      days,
      sourceFilter: source,
      overview: this.computeOverview(sessions),
      models: this.computeModelBreakdown(sessions),
      platforms: this.computePlatformBreakdown(sessions),
      tools: this.computeToolRanking(toolUsage),
      skills: this.computeSkillUsage(skillUsage),
      activity: this.computeActivityTrend(sessions),
      topSessions: this.computeTopSessions(sessions)
    };
  }
  
  formatTerminal(report: InsightsReport): string {
    const lines: string[] = [];
    
    // 概览
    lines.push('## 概览');
    lines.push(`会话数: ${report.overview.totalSessions}`);
    lines.push(`消息数: ${report.overview.totalMessages}`);
    lines.push(`Token: ${formatCompact(report.overview.totalTokens)}`);
    lines.push(`成本: $${report.overview.estimatedCost.toFixed(2)}`);
    
    // 活动趋势（条形图）
    lines.push('\n## 每日活动');
    lines.push(this.formatBarChart(report.activity.dailySessions));
    
    return lines.join('\n');
  }
  
  private formatBarChart(values: number[], maxWidth: number = 20): string {
    const peak = Math.max(...values, 1);
    return values.map(v => '█'.repeat(Math.max(1, Math.floor(v / peak * maxWidth)))).join('\n');
  }
}
```

### 2. 成本估算

```typescript
export function estimateCost(model: string, usage: TokenUsage, provider?: string): CostEstimate {
  const pricing = PRICING_DATABASE[model];
  
  if (!pricing) {
    return { amountUsd: 0, status: 'unknown' };
  }
  
  const inputCost = usage.inputTokens * pricing.inputPerToken;
  const outputCost = usage.outputTokens * pricing.outputPerToken;
  const cacheReadCost = usage.cacheReadTokens * pricing.cacheReadPerToken;
  const cacheWriteCost = usage.cacheWriteTokens * pricing.cacheWritePerToken;
  
  return {
    amountUsd: inputCost + outputCost + cacheReadCost + cacheWriteCost,
    status: 'estimated'
  };
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| 模型定价数据可能过时 | 预留定价数据库更新接口 |
| 成本估算不准确 | 标记为 "estimated"，实际成本可能不同 |
| 大量会话查询可能慢 | 使用索引优化查询，限制时间范围 |
