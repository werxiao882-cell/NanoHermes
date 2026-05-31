## ADDED Requirements

### Requirement: 工具函数桥接

系统 SHALL 提供桥接函数，将 NanoHermes 内部工具函数转换为 MCP 兼容格式。

#### Scenario: 桥接简单工具函数
- **WHEN** 调用 `bridge_tool()` 包装一个接受字符串参数并返回字符串的工具函数
- **THEN** 返回 MCP 兼容的可调用对象，参数 schema 正确转换

#### Scenario: 桥接带 Pydantic 参数的工具
- **WHEN** 调用 `bridge_tool()` 包装一个使用 Pydantic model 定义参数的工具函数
- **THEN** Pydantic schema 自动转换为 JSON Schema 格式

#### Scenario: 错误处理
- **WHEN** 桥接的工具函数执行时抛出异常
- **THEN** 异常被捕获并转换为 MCP 标准错误响应格式

### Requirement: 参数 Schema 转换

系统 SHALL 将 NanoHermes 工具的参数定义转换为 MCP 工具参数 JSON Schema。

#### Scenario: 基本类型转换
- **WHEN** 工具参数包含 str、int、float、bool 类型
- **THEN** 转换为对应的 JSON Schema type 字段

#### Scenario: 可选参数处理
- **WHEN** 工具参数有默认值
- **THEN** 该参数在 JSON Schema 中标记为非 required

### Requirement: 返回值格式化

系统 SHALL 将工具函数的返回值格式化为 MCP 标准响应格式。

#### Scenario: 成功响应
- **WHEN** 工具函数执行成功
- **THEN** 返回包含 `content` 字段的 MCP 响应，内容为 TextContent 列表

#### Scenario: 错误响应
- **WHEN** 工具函数执行失败
- **THEN** 返回包含错误描述的 ErrorContent
