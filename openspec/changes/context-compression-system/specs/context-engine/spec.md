## ContextEngine 抽象基类

### 需求

- **MUST** 定义 `ContextEngine` 抽象基类，包含 3 个核心抽象方法：`update_from_response`, `should_compress`, `compress`
- **MUST** 实现可选工具接口：`get_tool_schemas`, `handle_tool_call`
- **MUST** 允许第三方引擎通过配置替换内置压缩器
