# Design: 网络搜索工具

## 架构决策

### 为什么选择 DuckDuckGo？

| 方案 | 优势 | 劣势 |
|------|------|------|
| DuckDuckGo | 无需 API Key、隐私友好、Python 库成熟 | 结果质量略低于 Google |
| Google Custom Search | 结果质量高 | 需要 API Key、有配额限制 |
| Bing Search API | 结果质量高 | 需要 API Key、付费 |
| SerpAPI | 聚合多引擎 | 付费、依赖第三方 |

**结论**: DuckDuckGo 最适合 NanoHermes 的定位（轻量、零配置、开箱即用）。

### 为什么使用延迟加载？

- `web_search` 不是每次对话都需要的工具
- 延迟加载避免占用核心工具上下文（6 个核心工具已占约 2000 tokens）
- 用户通过 `search_tools(query="web search")` 按需发现

### 搜索结果格式化策略

- **text 模式**: 返回 title + url + description（3 字段）
- **news 模式**: 返回 title + url + description + source + date（5 字段）
- 不返回完整网页内容（避免占满上下文），LLM 可通过 `read_file` 或其他方式获取详情

## 参数设计

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| query | string | 是 | - | 搜索关键词 |
| max_results | int | 否 | 5 | 最大结果数（1-20） |
| region | string | 否 | "wt-wt" | 搜索区域 |
| safesearch | string | 否 | "moderate" | 安全级别 |
| timelimit | string | 否 | None | 时间限制 (d/w/m/y) |
| backend | string | 否 | "text" | 搜索类型 (text/news) |

## 错误处理

| 场景 | 处理方式 |
|------|----------|
| duckduckgo-search 未安装 | 返回 JSON error + 安装提示 |
| 空查询 | 返回 JSON error |
| 网络异常 | 捕获异常，返回 JSON error + 异常详情 |
| 无结果 | 返回 status=success + count=0 |
| max_results 超限 | 自动 clamp 到 [1, 20] |

## 模块位置

```
src/tools/impls/web_search_tool.py  # 工具实现
tests/tools/test_web_search_tool.py # 测试
```

工具通过 `register_tool()` 在模块加载时自动注册，归入 `search` toolset。
