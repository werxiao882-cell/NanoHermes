## ADDED Requirements

### Requirement: Curator 空闲触发 SHALL 正确工作
测试 SHALL 验证空闲检测和间隔检查。

#### Scenario: 空闲时触发
- **GIVEN** Curator 实例，最后运行时间 > interval_hours 前
- **WHEN** 调用 maybeRun，Agent 空闲 > min_idle_hours
- **THEN** 执行审查流程

#### Scenario: 未空闲不触发
- **GIVEN** Curator 实例
- **WHEN** 调用 maybeRun，Agent 活跃
- **THEN** 不执行审查

#### Scenario: 间隔未到不触发
- **GIVEN** Curator 实例，最后运行时间 < interval_hours 前
- **WHEN** 调用 maybeRun
- **THEN** 不执行审查

### Requirement: Curator 自动转换状态 SHALL 正确工作
测试 SHALL 验证 active → stale → archived 转换。

#### Scenario: 转换为 stale
- **GIVEN** 技能最后活动 > stale_after_days 前
- **WHEN** 调用 autoTransitions
- **THEN** 技能状态变为 stale

#### Scenario: 转换为 archived
- **GIVEN** 技能状态为 stale，最后活动 > archive_after_days 前
- **WHEN** 调用 autoTransitions
- **THEN** 技能被移动到归档目录

#### Scenario: pinned 技能不转换
- **GIVEN** pinned 技能，最后活动 > archive_after_days 前
- **WHEN** 调用 autoTransitions
- **THEN** 技能保持 active 状态

### Requirement: Curator 备份 SHALL 正确工作
测试 SHALL 验证 tar.gz 备份创建。

#### Scenario: 创建备份
- **GIVEN** Curator 实例
- **WHEN** 调用 backup
- **THEN** 创建带时间戳的 tar.gz 文件
- **AND** 包含所有技能文件
