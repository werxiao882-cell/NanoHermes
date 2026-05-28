# Insights Metrics Architecture

## Responsibility
洞察引擎，分析会话数据生成使用情况报告。
包含 token 消耗聚合、成本估算、工具使用模式、活动趋势。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    Session Database                           │
│                  (SQLite + JSONL)                             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    InsightsEngine                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Data Aggregation                                       │  │
│  │  - Query sessions table for metadata                   │  │
│  │  - Aggregate token counts across sessions              │  │
│  │  - Calculate total cost from pricing data              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Report Generation                                      │  │
│  │  - Overview: total sessions, messages, tokens, cost    │  │
│  │  - Model breakdown: usage by model                     │  │
│  │  - Tool ranking: most used tools                       │  │
│  │  - Daily activity: sessions/messages/tokens per day    │  │
│  │  - Top sessions: highest token usage sessions          │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  InsightsReport                                         │  │
│  │  - total_sessions, total_messages, total_tokens        │  │
│  │  - total_cost (USD)                                    │  │
│  │  - model_breakdown, tool_ranking                       │  │
│  │  - daily_activity, top_sessions                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow
1. InsightsEngine 查询 SessionDB 获取所有会话数据
2. 聚合 token 计数（input + output + cache_read + cache_write）
3. 使用 ModelMetadata 的定价数据计算成本
4. 按模型、工具、日期分组统计
5. 生成 InsightsReport 返回给调用方

## Design Decisions
- **Decision**: 成本估算基于 token 计数和定价数据
  - **Reason**: 准确反映实际使用情况
- **Decision**: 报告包含多个维度的分析
  - **Reason**: 提供全面的洞察，帮助用户了解使用模式

## Dependencies
- Internal: src/session/session_db.py, src/provider/model_metadata.py
- External: None
