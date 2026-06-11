## Context

当前 NanoHermes 使用 ToolRegistry 单例管理所有工具，启动时通过 `init_all_tools()` 或 `discover_tools()` 加载所有工具定义。`get_tool_schemas()` 返回全部 schema 列表，传递给 LLM API。工具数量增长时，所有工具定义一次性占用大量上下文空间。

## Goals / Non-Goals

**Goals:**
- 启动时仅加载少量高频工具（5 个），其余工具标记为 defer_loading
- 模型通过内置 `search_tools` 工具按需发现延迟加载的工具
- 搜索引擎支持 BM25（自然语言）和 Regex 两种策略
- 每轮对话动态合并 always_loaded + discovered tools 传递给模型
- 向后兼容：现有工具默认 defer_loading=False，行为不变

**Non-Goals:**
- 不实现工具使用频率自动排序（手动标记 defer_loading）
- 不实现 MCP 协议集成（仅管理本地工具注册表）
- 不实现工具定义压缩（仅解决加载策略问题）

## Decisions

### 1. BM25 纯 Python 实现，无外部依赖

**决策**: 使用纯 Python 实现 BM25 算法，不引入 scikit-learn 等外部库。
**理由**: 项目依赖应保持轻量，BM25 算法简单（倒排索引 + 评分公式），纯 Python 实现约 100 行。
**替代方案**: 使用 `rank_bm25` 库（需额外依赖），或使用 TF-IDF（效果不如 BM25）。

### 2. search_tools 作为内置工具，始终可见

**决策**: `search_tools` 工具设置 `defer_loading=False`，始终在上下文中可见。
**理由**: 如果 search_tools 本身也被延迟加载，模型无法发现它，形成死锁。
**替代方案**: 将搜索能力内置为系统提示的一部分（但会占用固定上下文）。

### 3. ConversationLoop 管理 discovered tools 状态

**决策**: 在 ConversationLoop 中维护 `_discovered_tools` 字典，每轮合并到 current_tools。
**理由**: ConversationLoop 是对话状态的所有者，工具可见性是对话状态的一部分。
**替代方案**: 在 TUI 层管理（违反职责分离），或在 provider 层管理（耦合过深）。

### 4. search_tools 返回完整 schema 而非仅名称

**决策**: 搜索结果返回完整 OpenAI schema（name, description, parameters）。
**理由**: 模型需要完整 schema 才能理解工具功能和参数，仅返回名称需要二次查询。
**替代方案**: 先返回名称列表，模型再按需获取 schema（增加往返延迟）。

### 5. Auto 模式自动选择 BM25 或 Regex

**决策**: query 包含正则特征字符（`.*`, `[]`, `()`, `^`, `$`）时使用 Regex，否则 BM25。
**理由**: 降低模型选择负担，自动匹配最佳策略。
**替代方案**: 始终使用 BM25（正则场景效果差），或让模型指定 mode（增加复杂度）。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 模型不知道 search_tools 的存在 | 系统提示中明确说明 search_tools 的用法 |
| 搜索返回不相关工具 | BM25 k1/b 参数调优，top_k 限制为 5 |
| 搜索增加额外 API 调用 | 一次搜索发现多个工具，摊销开销 |
| defer_loading 工具无法在首轮使用 | 保留 5 个高频工具始终加载，覆盖常见场景 |
| 正则搜索语法错误 | 捕获 re.error，降级为 BM25 或返回空结果 |
