## ADDED Requirements

### Requirement: 子 Agent spawn SHALL 隔离上下文
测试 SHALL 验证子 Agent 上下文隔离。

#### Scenario: 子 Agent 无父历史
- **GIVEN** 父 Agent 有 10 条对话消息
- **WHEN** spawn 子 Agent
- **THEN** 子 Agent 的消息列表为空
- **AND** 子 Agent 的系统提示包含委托目标

#### Scenario: 父上下文只看到摘要
- **GIVEN** 子 Agent 完成 5 轮工具调用
- **WHEN** 子 Agent 返回
- **THEN** 父上下文只包含委托调用和摘要
- **AND** 不包含子 Agent 的工具调用
