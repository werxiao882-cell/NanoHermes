## ADDED Requirements

### Requirement: MemoryProvider 抽象类 SHALL 正确定义接口
测试 SHALL 验证抽象类的方法和默认实现。

#### Scenario: 实现核心方法
- **GIVEN** 一个继承 MemoryProvider 的类
- **WHEN** 不实现 `name` 属性、`is_available`、`initialize`、`system_prompt_block`
- **THEN** Python 抛出 TypeError（无法实例化抽象类）

#### Scenario: 可选钩子有默认实现
- **GIVEN** 一个继承 MemoryProvider 的类
- **WHEN** 不覆盖 `system_prompt_block`
- **THEN** 返回空字符串

#### Scenario: 覆盖可选钩子
- **GIVEN** 一个继承 MemoryProvider 的类
- **WHEN** 覆盖 `on_session_end`
- **THEN** 调用时使用正确的参数

### Requirement: initialize 方法 SHALL 接收正确的选项
测试 SHALL 验证 initialize 方法接收 session_id 和 kwargs 参数。

#### Scenario: 接收完整选项
- **GIVEN** MemoryProvider 实例
- **WHEN** 调用 `initialize('session-1', hermes_home='/tmp', platform='cli', agent_context='primary')`
- **THEN** 所有选项被正确传递

#### Scenario: 跳过非 primary 上下文
- **GIVEN** MemoryProvider 实例
- **WHEN** `agent_context='cron'`
- **THEN** 提供者跳过写入操作
