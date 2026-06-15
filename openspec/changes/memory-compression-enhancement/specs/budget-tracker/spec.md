## ADDED Requirements

### Requirement: 压缩记录追踪
系统 SHALL 记录每次压缩的 token 使用情况。

#### Scenario: 记录压缩事件
- **WHEN** 调用 `track_compression(before_tokens, after_tokens)`
- **THEN** 系统将压缩记录添加到历史缓冲区
- **AND** 记录包含 `before_tokens`、`after_tokens`、`saved_tokens`、`compression_ratio`、`timestamp`

#### Scenario: 计算节省的 token 数
- **WHEN** 压缩前 1000 tokens，压缩后 600 tokens
- **THEN** `saved_tokens` = 400
- **AND** `compression_ratio` = 0.6

### Requirement: 环形缓冲区存储
系统 SHALL 使用环形缓冲区存储压缩历史，固定内存占用。

#### Scenario: 缓冲区容量限制
- **WHEN** 初始化时指定 `max_history=100`
- **THEN** 最多保留最近 100 条压缩记录
- **AND** 超过 100 条时自动淘汰最旧的记录

#### Scenario: 默认缓冲区大小
- **WHEN** 未指定 `max_history`
- **THEN** 默认保留最近 100 条记录

### Requirement: 压缩效率统计
系统 SHALL 提供压缩效率统计接口。

#### Scenario: 计算平均压缩比
- **WHEN** 历史包含 3 条记录：ratio=0.5, 0.6, 0.7
- **THEN** `get_average_compression_ratio()` 返回 0.6

#### Scenario: 无历史记录时返回默认值
- **WHEN** 历史为空
- **THEN** `get_average_compression_ratio()` 返回 1.0（无压缩）

#### Scenario: 计算总节省 token 数
- **WHEN** 历史包含 3 条记录：saved=100, 200, 300
- **THEN** `get_total_tokens_saved()` 返回 600

#### Scenario: 计算压缩成功率
- **WHEN** 历史包含 5 条记录，其中 4 条成功
- **THEN** `get_success_rate()` 返回 0.8

### Requirement: 预算追踪器状态查询
系统 SHALL 提供预算追踪器状态查询接口。

#### Scenario: 查询历史记录数量
- **WHEN** 调用 `history_count` 属性
- **THEN** 返回当前历史记录数量

#### Scenario: 查询历史记录
- **WHEN** 调用 `get_history()` 方法
- **THEN** 返回历史记录列表（按时间倒序）

#### Scenario: 查询最近 N 条记录
- **WHEN** 调用 `get_history(limit=10)`
- **THEN** 返回最近 10 条记录

### Requirement: 预算追踪器重置
系统 SHALL 支持重置预算追踪器。

#### Scenario: 清空历史记录
- **WHEN** 调用 `reset()` 方法
- **THEN** 历史记录清空
- **AND** `history_count` 返回 0
