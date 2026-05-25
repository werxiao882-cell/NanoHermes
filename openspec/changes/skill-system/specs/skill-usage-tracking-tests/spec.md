## ADDED Requirements

### Requirement: 技能使用追踪 SHALL 正确记录
测试 SHALL 验证使用计数更新。

#### Scenario: 记录技能调用
- **GIVEN** 技能使用追踪器
- **WHEN** 技能被调用
- **THEN** use_count 递增
- **AND** last_activity_at 更新为当前时间

#### Scenario: 记录技能查看
- **GIVEN** 技能使用追踪器
- **WHEN** 技能被查看
- **THEN** view_count 递增

#### Scenario: 记录技能补丁
- **GIVEN** 技能使用追踪器
- **WHEN** 技能被补丁
- **THEN** patch_count 递增
- **AND** last_activity_at 更新
