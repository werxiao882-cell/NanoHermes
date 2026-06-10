## 1. 依赖安装

- [x] 1.1 在 `pyproject.toml` 的 dependencies 中添加 `duckduckgo-search>=6.0.0`
- [x] 1.2 验证安装成功：`pip install duckduckgo-search`
- [x] 1.3 快速验证：`python -c "from duckduckgo_search import DDGS; print('ok')"`

## 2. 工具实现

- [x] 2.1 创建 `src/tools/web_search_tool.py` 文件
- [x] 2.2 实现 `web_search` 主函数，支持以下参数：
  - `query`（必填）：搜索关键词
  - `max_results`（可选，默认 5）：最大返回结果数
  - `region`（可选，默认 "wt-wt"）：搜索区域，支持 zh-cn、en-us 等
  - `safesearch`（可选，默认 "moderate"）：安全级别（on/moderate/off）
  - `timelimit`（可选）：时间限制（d/w/m/y 分别表示日/周/月/年）
  - `backend`（可选，默认 "text"）：搜索后端（text/news）
  - `task_id`（可选）：任务 ID
- [x] 2.3 实现 text 搜索模式：使用 `DDGS.text()` 获取结果
- [x] 2.4 实现 news 搜索模式：使用 `DDGS.news()` 获取结果
- [x] 2.5 实现结果格式化：返回包含 title、url、description、source 的结构化 JSON
- [x] 2.6 实现错误处理：网络异常、API 限流、无结果等场景
- [x] 2.7 实现 `check_web_search_available()` 可用性检查函数
- [x] 2.8 调用 `register_tool()` 注册工具到全局注册表
- [x] 2.9 工具 schema 设计：参考 Hermes Agent 的 web_search 工具描述

## 3. 工具集更新

- [x] 3.1 在 `src/tools/toolsets.py` 的 `TOOLSETS` 中添加 `"search": ["web_search"]`
- [x] 3.2 在 `src/tools/registry.py` 的 `tool_modules` 列表中添加 `"src.tools.web_search_tool"`

## 4. 测试

- [x] 4.1 创建 `tests/tools/test_web_search_tool.py`
- [x] 4.2 编写可用性检查测试（mock 依赖可用/不可用场景）
- [x] 4.3 编写注册验证测试（验证工具已正确注册到 ToolRegistry）
- [x] 4.4 编写 schema 验证测试（验证 schema 包含必要字段）
- [x] 4.5 编写错误处理测试（mock DDGS 抛出异常的场景）
- [x] 4.6 编写结果格式化测试（验证返回的 JSON 结构正确）

## 5. 验证

- [x] 5.1 运行 `pytest tests/tools/test_web_search_tool.py -v` 全部通过
- [x] 5.2 运行 `pytest tests/tools/ -v` 确认不影响现有工具测试
- [x] 5.3 手动验证：`python -c "from src.tools.web_search_tool import web_search; print(web_search('Python 3.12', max_results=3))"`
