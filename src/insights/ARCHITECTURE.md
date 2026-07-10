# Insights 模块架构

## 模块概述

洞察/指标模块，分析会话数据生成使用情况报告。支持 token 消耗聚合、成本估算（基于硬编码定价数据库）、工具/技能使用模式分析、活动趋势追踪。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块入口，导出 `InsightsEngine` |
| `engine.py` | 核心实现：定价数据库、数据聚合引擎、报告容器、终端格式化 |

## 核心数据流

```
SessionDB (SQLite)
    │
    ▼  _get_all_sessions() → SELECT * FROM sessions
┌──────────────────────────────────────────────────┐
│                  InsightsEngine                  │
│                                                  │
│  get_sessions(source?, limit?)                   │
│    │  过滤 + 截取                                │
│    ▼                                             │
│  generate_report()                               │
│    ├── compute_model_breakdown()    ─┐            │
│    ├── compute_platform_breakdown() ─┤ 多维度     │
│    ├── compute_tool_ranking()       ─┤ 聚合       │
│    ├── compute_skill_usage()        ─┤            │
│    ├── compute_activity_trend()     ─┤            │
│    ├── compute_top_sessions()       ─┘            │
│    ├── _compute_total_cost()  → estimate_cost()  │
│    └── _compute_message_stats()                  │
│              │                                   │
│              ▼                                   │
│        InsightsReport (dataclass)                │
│              │                                   │
│              ▼                                   │
│        format_terminal() → 终端字符串输出          │
└──────────────────────────────────────────────────┘
```

## 关键设计决策

1. **定价数据库硬编码** (`PRICING_DATABASE`)
   - 原因：定价变更频率低（季度级别），避免运行时文件 I/O 和网络依赖，保证离线可用性
   - 支持四种定价维度：input / output / cache_read / cache_write（USD / 1M tokens）
   - 包含 default 条目，未知模型回退到 Claude Sonnet 价格

2. **成本匹配策略** (`estimate_cost()`)
   - 精确匹配 → 部分匹配（双向子串）→ default 回退
   - 原因：模型名称可能含后缀（如 `-thinking`），部分匹配提升覆盖率

3. **无状态引擎**
   - 每次 `generate_report()` 重新查询数据库，避免缓存不一致
   - `session_db` 通过构造函数注入，便于测试 mock

4. **InsightsReport 使用 dataclass**
   - 类型安全 + IDE 补全，所有字段有默认值支持渐进式填充
   - `default_factory=list` 避免可变默认值陷阱

5. **工具/技能调用容错解析**
   - `tool_calls` / `skills_used` 可能是 JSON 字符串、字典列表或字符串列表
   - 动态解析 + 回退到空列表，避免数据格式不一致导致崩溃

## 对外接口

### 公共类

- **`InsightsEngine(session_db)`** — 洞察引擎主类
  - `generate_report(*, source?, limit?, include_cost?)` → `InsightsReport`
  - `get_sessions(*, source?, limit?)` → `list[dict]`
  - `get_tool_usage(sessions?)` → `list[dict]`
  - `get_skill_usage(sessions?)` → `list[dict]`
  - `get_message_stats(sessions?)` → `dict`
  - `compute_overview(sessions)` → `dict`
  - `compute_model_breakdown(sessions)` → `list[dict]`
  - `compute_platform_breakdown(sessions)` → `list[dict]`
  - `compute_tool_ranking(sessions)` → `list[dict]`
  - `compute_skill_usage(sessions)` → `list[dict]`
  - `compute_activity_trend(sessions)` → `list[dict]`
  - `compute_top_sessions(sessions, top_n?, sort_by?)` → `list[dict]`
  - `format_terminal(report?, width?)` → `str`
  - `format_bar_chart(data, key?, max_width?)` → `str`

- **`InsightsReport`** — 报告数据容器 (dataclass)
  - 字段：`total_sessions`, `total_messages`, `total_tokens`, `total_cost`, `model_breakdown`, `platform_breakdown`, `tool_ranking`, `skill_usage`, `daily_activity`, `top_sessions`, `message_stats`
  - `format_terminal(width?)` → `str`

### 公共函数

- **`estimate_cost(model, input_tokens?, output_tokens?, cache_read_tokens?, cache_write_tokens?)`** → `float` — 独立成本估算函数
- **`format_terminal(report, width?)`** → `str` — 报告终端格式化
- **`format_bar_chart(data, key?, max_width?)`** → `str` — ASCII 条形图生成

### 模块常量

- **`PRICING_DATABASE`** — `dict[str, dict[str, float]]`，模型定价表（USD / 1M tokens）

## 依赖关系

| 方向 | 模块 | 用途 |
|------|------|------|
| 使用 → | `src/session/` (SessionDB) | 通过注入的 `session_db` 查询 sessions 表（`SELECT * FROM sessions`） |
| ← 被使用 | `src/cli/` 或调用方 | 通过 `InsightsEngine` 生成报告并格式化输出 |

**标准库依赖**：`json`, `math`, `collections` (Counter, defaultdict), `dataclasses`, `datetime`

**无外部依赖**。
