## ADDED Requirements

### Requirement: 熔断器状态机
系统 SHALL 实现三状态熔断器（CLOSED、OPEN、HALF_OPEN），用于防止压缩循环。

#### Scenario: 正常状态允许压缩
- **WHEN** 熔断器状态为 CLOSED
- **THEN** `can_compress()` 返回 `True`

#### Scenario: 连续失败触发熔断
- **WHEN** 连续失败次数达到 `failure_threshold`（默认 3）
- **THEN** 熔断器状态转换为 OPEN
- **AND** `can_compress()` 返回 `False`

#### Scenario: 冷却期后进入探测状态
- **WHEN** 熔断器状态为 OPEN 且距离上次失败时间超过 `cooldown_seconds`（默认 60 秒）
- **THEN** 熔断器状态转换为 HALF_OPEN
- **AND** `can_compress()` 返回 `True`

#### Scenario: 探测成功恢复
- **WHEN** 熔断器状态为 HALF_OPEN 且压缩成功
- **THEN** 熔断器状态转换为 CLOSED
- **AND** 失败计数器重置为 0

#### Scenario: 探测失败继续熔断
- **WHEN** 熔断器状态为 HALF_OPEN 且压缩失败
- **THEN** 熔断器状态转换为 OPEN
- **AND** 更新最后失败时间

### Requirement: 熔断器配置
系统 SHALL 支持可配置的熔断器参数。

#### Scenario: 自定义失败阈值
- **WHEN** 初始化熔断器时指定 `failure_threshold=5`
- **THEN** 连续 5 次失败后触发熔断

#### Scenario: 自定义冷却期
- **WHEN** 初始化熔断器时指定 `cooldown_seconds=120`
- **THEN** 熔断后 120 秒进入探测状态

### Requirement: 熔断器状态查询
系统 SHALL 提供熔断器状态查询接口。

#### Scenario: 查询当前状态
- **WHEN** 调用 `state` 属性
- **THEN** 返回当前状态（"CLOSED"、"OPEN" 或 "HALF_OPEN"）

#### Scenario: 查询失败计数
- **WHEN** 调用 `failure_count` 属性
- **THEN** 返回当前连续失败次数

#### Scenario: 查询最后失败时间
- **WHEN** 调用 `last_failure_time` 属性
- **THEN** 返回最后失败的时间戳（Unix 时间）

### Requirement: 熔断器重置
系统 SHALL 支持手动重置熔断器状态。

#### Scenario: 手动重置
- **WHEN** 调用 `reset()` 方法
- **THEN** 熔断器状态转换为 CLOSED
- **AND** 失败计数器重置为 0
- **AND** 最后失败时间清空
