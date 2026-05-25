## ADDED Requirements

### Requirement: 技能生命周期状态转换 SHALL 正确工作
测试 SHALL 验证状态转换逻辑。

#### Scenario: active → stale
- **GIVEN** 技能状态为 active，最后活动 > stale_after_days
- **WHEN** 调用 markStale
- **THEN** 状态变为 stale

#### Scenario: stale → archived
- **GIVEN** 技能状态为 stale，最后活动 > archive_after_days
- **WHEN** 调用 archiveSkill
- **THEN** 技能移动到归档目录
- **AND** 状态变为 archived

#### Scenario: 恢复归档技能
- **GIVEN** 技能状态为 archived
- **WHEN** 调用 restoreSkill
- **THEN** 技能移回活动目录
- **AND** 状态变为 active
