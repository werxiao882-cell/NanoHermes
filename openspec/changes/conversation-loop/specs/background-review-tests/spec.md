## ADDED Requirements

### Requirement: 后台审查 SHALL fork Agent 并评估
测试 SHALL 验证审查线程行为。

#### Scenario: fork Agent 继承配置
- **GIVEN** 父 Agent 配置
- **WHEN** forkAgent 被调用
- **THEN** 子 Agent 继承 provider、model、base_url
- **AND** 工具白名单为 ['memory', 'skill_manage']

#### Scenario: 审查记忆
- **GIVEN** 对话包含用户偏好信息
- **WHEN** 后台审查运行
- **THEN** 审查 Agent 使用 memory 工具保存偏好

#### Scenario: 审查技能
- **GIVEN** 对话包含新技术或工作流
- **WHEN** 后台审查运行
- **THEN** 审查 Agent 使用 skill_manage 更新技能

#### Scenario: 无内容可保存
- **GIVEN** 对话无值得保存的内容
- **WHEN** 后台审查运行
- **THEN** 审查 Agent 返回 "Nothing to save."
