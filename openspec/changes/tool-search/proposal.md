## Why

当前系统启动时将所有工具定义（schema）一次性加载到 LLM 上下文中。工具数量增长时，工具定义占用大量上下文空间（39 个工具 ≈ 31K tokens，极端场景 134K tokens），且工具越多模型越容易选错。参考 Claude Code 2.1.69 的 Tool Search 机制，改为"按需发现"模式：启动时仅加载少量高频工具，其余工具通过搜索引擎动态发现。

## What Changes

- `ToolEntry` 新增 `defer_loading` 字段，标记工具是否延迟加载
- `ToolRegistry` 新增 `get_deferred_tools()` 和 `get_tool_schemas(exclude_deferred)` 方法
- 新增 `ToolSearch` 类：BM25 + Regex 双引擎工具搜索引擎
- 新增内置工具 `search_tools`：模型通过此工具按需发现延迟加载的工具
- `ConversationLoop` 支持动态工具管理：每轮合并 always_loaded + discovered tools
- 模型调用 `search_tools` 后，搜索结果自动加入下一轮可用工具集

## Capabilities

### New Capabilities

- `tool-defer-loading`: 工具延迟加载标记机制，支持 `defer_loading` 字段和过滤查询
- `tool-search-engine`: BM25 + Regex 双引擎工具搜索，支持自然语言和正则查询
- `tool-search-tool`: 内置 `search_tools` 工具，模型通过此工具动态发现延迟加载的工具
- `dynamic-tool-discovery`: ConversationLoop 动态工具管理，每轮合并已发现工具到上下文

### Modified Capabilities

- `tool-registry`: `ToolEntry` 数据结构扩展，`get_tool_schemas()` 支持 exclude_deferred 参数

## Impact

- `src/tools/registry.py`: ToolEntry 新增字段，注册表新增过滤方法
- `src/tools/tool_search.py`: 新建搜索引擎模块
- `src/tools/search_tool.py`: 新建 search_tools 工具
- `src/conversation/loop.py`: 动态工具管理逻辑
- `src/main.py`: 初始化 ToolSearch 并注入 ConversationLoop
- 现有工具可选添加 `defer_loading=True`，不影响向后兼容
