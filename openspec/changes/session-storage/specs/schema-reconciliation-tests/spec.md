## ADDED Requirements

### Requirement: _parse_schema_columns 方法 SHALL 正确解析期望列

测试 SHALL 验证使用内存 SQLite 解析 SCHEMA_SQL 并提取期望列。

#### Scenario: 解析单表列
- **GIVEN** SessionDB 实例
- **WHEN** 调用 _parse_schema_columns
- **THEN** 返回包含表名和列名的映射

#### Scenario: 解析多表列
- **GIVEN** SessionDB 实例，包含 sessions 和 messages 表
- **WHEN** 调用 _parse_schema_columns
- **THEN** 返回两个表的所有列

#### Scenario: 解析带 DEFAULT 的列
- **GIVEN** SessionDB 实例，包含带 DEFAULT 值的列
- **WHEN** 调用 _parse_schema_columns
- **THEN** 列类型表达式包含 DEFAULT 值

### Requirement: _reconcile_columns 方法 SHALL 添加缺失列

测试 SHALL 验证对比 live 列和期望列，自动添加缺失列。

#### Scenario: 添加缺失列
- **GIVEN** SessionDB 实例，缺少某个列
- **WHEN** 调用 _reconcile_columns
- **THEN** 执行 ALTER TABLE ADD COLUMN 添加缺失列

#### Scenario: 不添加已存在的列
- **GIVEN** SessionDB 实例，所有列已存在
- **WHEN** 调用 _reconcile_columns
- **THEN** 不执行任何 ALTER TABLE 操作

#### Scenario: 处理重复列错误
- **GIVEN** SessionDB 实例
- **WHEN** 调用 _reconcile_columns 且列已存在
- **THEN** 捕获错误并记录 debug 日志，不抛出异常

### Requirement: 索引创建 SHALL 在协调之后

测试 SHALL 验证依赖协调添加列的索引在协调后创建。

#### Scenario: 延迟索引创建
- **GIVEN** SessionDB 实例，协调后添加新列
- **THEN** 索引在 _reconcile_columns 之后创建

#### Scenario: 索引创建失败不阻塞启动
- **GIVEN** 索引创建失败（列不存在）
- **WHEN** 初始化 SessionDB
- **THEN** 记录 DEBUG 日志，不抛出错误

### Requirement: schema_version 表 SHALL 跟踪版本
测试 SHALL 验证 schema_version 表的初始化和更新。

#### Scenario: 初始化 schema_version
- **GIVEN** 新数据库
- **WHEN** 初始化 SessionDB
- **THEN** schema_version 表包含当前 SCHEMA_VERSION

#### Scenario: 更新 schema_version
- **GIVEN** 数据库版本为 5，当前 SCHEMA_VERSION 为 13
- **WHEN** 初始化 SessionDB
- **THEN** schema_version 更新为 13
