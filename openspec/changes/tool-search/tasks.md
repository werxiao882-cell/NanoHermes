## 1. ToolEntry defer_loading 字段

- [x] 1.1 在 `ToolEntry` dataclass 新增 `defer_loading: bool = False` 字段
- [x] 1.2 `register_tool()` 函数新增 `defer_loading` 参数并传递给 ToolEntry
- [x] 1.3 `ToolRegistry.get_tool_schemas()` 新增 `exclude_deferred: bool = False` 参数
- [x] 1.4 `ToolRegistry.get_deferred_tools()` 新方法：返回所有 defer_loading=True 的条目
- [x] 1.5 模块级便捷函数 `get_deferred_tools()` 代理到 ToolRegistry

## 2. 现有工具添加 defer_loading 标记

以下 11 个工具需添加 `defer_loading=True`：

- [x] 2.1 `code_execution_tool.py`: `execute_code` 添加 `defer_loading=True`
- [x] 2.2 `terminal.py`: `process` 添加 `defer_loading=True`
- [x] 2.3 `todo_tool.py`: `todo` 添加 `defer_loading=True`
- [x] 2.4 `memory_tool.py`: `memory` 添加 `defer_loading=True`
- [x] 2.5 `session_search_tool.py`: `session_search` 添加 `defer_loading=True`
- [x] 2.6 `clarify_tool.py`: `clarify` 添加 `defer_loading=True`
- [x] 2.7 `skills_tool.py`: `skill_view` 添加 `defer_loading=True`
- [x] 2.8 `skills_tool.py`: `skills_list` 添加 `defer_loading=True`
- [x] 2.9 `skills_tool.py`: `skill_manage` 添加 `defer_loading=True`
- [x] 2.10 `delegation_tool.py`: `delegate_task` 添加 `defer_loading=True`
- [x] 2.11 `cronjob_tool.py`: `cronjob` 添加 `defer_loading=True`

以下 5 个工具保持 `defer_loading=False`（默认值，无需修改）：
`read_file`, `write_file`, `search_files`, `patch`（file_tool.py）、`terminal`（terminal.py）

## 3. ToolSearch 搜索引擎

- [x] 3.1 创建 `src/tools/tool_search.py` 模块和 `ToolSearch` 类
- [x] 3.2 实现 BM25 倒排索引构建：分词工具名、描述、参数名、参数描述
- [x] 3.3 实现 BM25 评分公式：`score = IDF * (f * (k1+1)) / (f + k1 * (1 - b + b * |D|/avgdl))`
- [x] 3.4 实现 Regex 搜索：编译 query 为正则，匹配工具名/描述/参数
- [x] 3.5 实现 Auto 模式：检测 regex 特征字符自动选择策略
- [x] 3.6 `search()` 方法：统一入口，返回 top_k 工具 schema 列表
- [x] 3.7 处理边界情况：空工具列表、无效正则、无匹配结果

## 4. search_tools 内置工具

- [x] 4.1 创建 `src/tools/search_tool.py` 模块
- [x] 4.2 实现 `search_tools_handler(query, mode)` 函数
- [x] 4.3 注册 `search_tools` 工具，`defer_loading=False`（始终可见）
- [x] 4.4 Schema 定义：`query`（必填）、`mode`（可选，默认 "auto"）
- [x] 4.5 将 `search_tool.py` 添加到 `init_all_tools()` 模块列表
- [x] 4.6 将 `search_tool.py` 从 AST 发现 skip_files 中移除（支持自动发现）

## 5. ConversationLoop 动态工具管理

- [x] 5.1 `ConversationLoop.__init__` 新增 `tool_search: ToolSearch | None` 参数
- [x] 5.2 新增 `_discovered_tools: dict[str, dict]` 属性
- [x] 5.3 `run()` 方法初始化 `_always_loaded_schemas` 从传入的 tools 参数
- [x] 5.4 每轮迭代前合并 `_always_loaded_schemas` + `_discovered_tools.values()`
- [x] 5.5 工具分发时检测 `search_tools` 调用，解析结果并添加到 `_discovered_tools`
- [x] 5.6 确保搜索结果的 tool message 仍正常追加到消息历史

## 6. main.py 集成

- [x] 6.1 初始化 ToolSearch 实例，传入 deferred tools 列表
- [x] 6.2 将 ToolSearch 注入 ConversationLoop 构造函数
- [x] 6.3 启动时 `get_tool_schemas(exclude_deferred=True)` 获取初始工具集
- [x] 6.4 验证初始工具集包含 6 个工具：5 个核心 + search_tools

## 7. 测试

- [x] 7.1 测试 ToolEntry defer_loading 默认值和显式设置
- [x] 7.2 测试 ToolRegistry.get_tool_schemas(exclude_deferred=True) 过滤
- [x] 7.3 测试 ToolRegistry.get_deferred_tools() 返回正确条目
- [x] 7.4 测试 5 个核心工具在初始集中，11 个工具在延迟集中
- [x] 7.5 测试 BM25 索引构建和评分
- [x] 7.6 测试 Regex 搜索匹配和无效正则处理
- [x] 7.7 测试 Auto 模式策略选择
- [x] 7.8 测试 search_tools 工具调用返回正确 JSON
- [x] 7.9 测试 ConversationLoop 动态工具发现和合并
- [x] 7.10 集成测试：完整流程（搜索 → 发现 → 调用 discovered tool）

## 8. TUI 工具显示

- [x] 8.1 `/tools` 命令显示每个工具的 `defer_loading` 状态（loaded/deferred）

## 9. 架构文档

- [x] 9.1 更新 `src/tools/ARCHITECTURE.md` 包含 Tool Search 机制
