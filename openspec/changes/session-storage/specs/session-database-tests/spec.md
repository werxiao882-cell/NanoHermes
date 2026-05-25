## ADDED Requirements

### Requirement: SessionDB 构造函数 SHALL 正确初始化数据库
测试 SHALL 验证 SessionDB 构造函数创建数据库文件、设置 WAL 模式、创建所有表和索引。

#### Scenario: 创建新数据库
- **GIVEN** 一个不存在的数据库路径
- **WHEN** 创建 SessionDB 实例
- **THEN** 数据库文件被创建
- **AND** sessions、messages、state_meta 表存在
- **AND** schema_version 表存在且版本为当前 SCHEMA_VERSION
- **AND** 所有索引被创建

#### Scenario: 打开已存在的数据库
- **GIVEN** 一个已存在的数据库文件
- **WHEN** 创建 SessionDB 实例
- **THEN** 数据库被成功打开
- **AND** 所有表结构保持不变

#### Scenario: WAL 模式设置
- **GIVEN** 一个支持 WAL 的文件系统
- **WHEN** SessionDB 初始化
- **THEN** journal_mode 被设置为 'wal'
- **AND** -wal 和 -shm 文件被创建

#### Scenario: WAL 回退到 DELETE 模式
- **GIVEN** 一个不支持 WAL 的文件系统（模拟 "locking protocol" 错误）
- **WHEN** SessionDB 初始化
- **THEN** journal_mode 回退到 'delete'
- **AND** 记录一次 WARNING 日志

#### Scenario: 外键约束启用
- **GIVEN** SessionDB 实例
- **WHEN** 查询 foreign_keys pragma
- **THEN** 返回 1（启用）

### Requirement: _executeWrite 方法 SHALL 处理写锁竞争
测试 SHALL 验证写操作在锁竞争时使用抖动重试，并在非锁定错误时立即传播。

#### Scenario: 成功写入无竞争
- **GIVEN** SessionDB 实例
- **WHEN** 执行写操作
- **THEN** 操作成功完成
- **AND** 事务被提交

#### Scenario: 锁竞争重试成功
- **GIVEN** SessionDB 实例，另一个连接持有写锁
- **WHEN** 执行写操作遇到 "database is locked" 错误
- **THEN** 系统等待 20-150ms 随机时间后重试
- **AND** 最多重试 15 次
- **AND** 锁释放后操作成功

#### Scenario: 达到最大重试次数
- **GIVEN** SessionDB 实例，另一个连接持续持有写锁
- **WHEN** 执行写操作 15 次重试后仍失败
- **THEN** 抛出 "database is locked after max retries" 错误

#### Scenario: 非锁定错误立即传播
- **GIVEN** SessionDB 实例
- **WHEN** 执行写操作遇到约束违反错误
- **THEN** 错误立即抛出，不进行重试
- **AND** 事务被回滚

### Requirement: _tryWalCheckpoint 方法 SHALL 定期执行 checkpoint
测试 SHALL 验证每 50 次写操作后执行 PASSIVE checkpoint。

#### Scenario: 定期 checkpoint
- **GIVEN** SessionDB 实例
- **WHEN** 执行 50 次写操作
- **THEN** 执行 PRAGMA wal_checkpoint(PASSIVE)
- **AND** 记录 checkpoint 结果

#### Scenario: checkpoint 失败不抛出异常
- **GIVEN** SessionDB 实例，checkpoint 操作失败
- **WHEN** 执行 _tryWalCheckpoint
- **THEN** 异常被捕获，不抛出

### Requirement: close 方法 SHALL 正确关闭数据库
测试 SHALL 验证 close 方法执行最终 checkpoint 并关闭连接。

#### Scenario: 正常关闭
- **GIVEN** SessionDB 实例
- **WHEN** 调用 close 方法
- **THEN** 执行 PRAGMA wal_checkpoint(PASSIVE)
- **AND** 数据库连接被关闭
- **AND** 后续操作抛出错误

#### Scenario: 重复关闭
- **GIVEN** SessionDB 实例，已调用 close
- **WHEN** 再次调用 close 方法
- **THEN** 不抛出异常（幂等操作）
