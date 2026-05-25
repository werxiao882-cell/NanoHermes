## ADDED Requirements

### Requirement: 对话循环 SHALL 正确处理工具调用
测试 SHALL 验证工具分发流程。

#### Scenario: 单轮工具调用
- **GIVEN** ConversationLoop 实例，模型返回工具调用
- **WHEN** 运行对话循环
- **THEN** 工具被分发
- **AND** 结果追加到消息列表
- **AND** 继续下一轮

#### Scenario: 多轮工具调用
- **GIVEN** ConversationLoop 实例，模型连续 3 轮返回工具调用
- **WHEN** 运行对话循环
- **THEN** 所有工具被分发
- **AND** apiCallCount=3

#### Scenario: 达到迭代限制
- **GIVEN** ConversationLoop 实例，maxIterations=5
- **WHEN** 模型连续 5 轮返回工具调用
- **THEN** 循环退出
- **AND** 返回 "达到最大迭代次数"

### Requirement: 中断检查 SHALL 停止循环
测试 SHALL 验证中断处理。

#### Scenario: 中断停止循环
- **GIVEN** ConversationLoop 实例，运行中
- **WHEN** 设置 interruptRequested=true
- **THEN** 循环在下一次迭代检查时退出
