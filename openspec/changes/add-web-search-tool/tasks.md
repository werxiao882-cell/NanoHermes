# Tasks: 添加网络搜索工具

## 1. 依赖安装

- [x] 1.1 安装 `duckduckgo-search>=6.0.0`
- [x] 1.2 验证安装成功

## 2. 工具实现

- [x] 2.1 创建 `src/tools/impls/web_search_tool.py`
- [x] 2.2 实现 `web_search` 主函数（query, max_results, region, safesearch, timelimit, backend）
- [x] 2.3 实现 text 搜索模式（DDGS.text()）
- [x] 2.4 实现 news 搜索模式（DDGS.news()）
- [x] 2.5 实现结果格式化（title, url, description, source, date）
- [x] 2.6 实现错误处理（网络异常、空查询、无结果）
- [x] 2.7 实现 `check_web_search_available()` 可用性检查
- [x] 2.8 调用 `register_tool()` 注册工具（defer_loading=True, toolset="search"）
- [x] 2.9 工具 schema 设计（OpenAI function calling 格式）

## 3. 测试

- [x] 3.1 创建 `tests/tools/test_web_search_tool.py`
- [x] 3.2 可用性检查测试
- [x] 3.3 注册验证测试
- [x] 3.4 schema 验证测试
- [x] 3.5 错误处理测试（空查询、网络异常）
- [x] 3.6 结果格式化测试（text/news 模式）
- [x] 3.7 max_results 边界测试（clamp 到 [1, 20]）
- [x] 3.8 dispatcher 集成测试

## 4. OpenSpec 设计文档

- [x] 4.1 创建 `proposal.md`
- [x] 4.2 创建 `design.md`
- [x] 4.3 创建 `specs/web-search/spec.md`

## 5. 验证

- [x] 5.1 `pytest tests/tools/test_web_search_tool.py -v` 全部通过（12/12）
