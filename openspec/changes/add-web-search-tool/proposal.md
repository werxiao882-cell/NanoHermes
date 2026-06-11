# Proposal: 添加网络搜索工具

## Why

NanoHermes 当前缺少实时信息获取能力。Agent 无法查询最新新闻、技术文档更新、API 变更等需要实时数据的场景。参考 Hermes Agent 和 Claude Code 均具备 web search 能力，NanoHermes 需要补齐这一短板。

## What Changes

- **新增 `web_search` 工具** — 基于 DuckDuckGo 搜索引擎，无需 API Key，隐私友好
- **支持两种搜索模式** — text（网页搜索）和 news（新闻搜索）
- **延迟加载** — 通过 `search_tools` 按需发现，不占用核心工具上下文
- **结构化输出** — 返回 JSON 格式结果（title, url, description），便于 LLM 引用

## Impact

- **新增文件**: `src/tools/impls/web_search_tool.py`
- **新增依赖**: `duckduckgo-search>=6.0.0`
- **新增测试**: `tests/tools/test_web_search_tool.py`
- **工具集**: 归入 `search` toolset，与 `search_files` 同组
