## ADDED Requirements

### Requirement: _parseSchemaColumns 方法 SHALL 正确解析期望列
测试 SHALL 验证使用内存 SQLite 数据库解析 SCHEMA_SQL 提取列定义。

#### Scenario: 解析单表列
- **GIVEN** SCHEMA_SQL 包含 sessions 表定义
- **WHEN** 调用 _parseSchemaColumns
- **THEN** 返回 sessions 表的所有列及其类型表达式

#### Scenario: 解析多表列
- **GIVEN** SCHEMA_SQL 包含 sessions、messages、state_meta 表
- **WHEN** 调用 _parseSchemaColumns
- **THEN** 返回所有表的列定义

#### Scenario: 解析带 DEFAULT 的列
- **GIVEN** 列定义包含 `message_count INTEGER DEFAULT 0`
- **WHEN** 调用 _parseSchemaColumns
- **THEN** 返回类型表达式 'INTEGER DEFAULT 0'

### Requirement: _reconcileColumns 方法 SHALL 添加缺失列
测试 SHALL 验证 live 列和期望列对比，自动添加缺失列。

#### Scenario: 添加缺失列
- **GIVEN** 数据库缺少 billing_provider 列
- **WHEN** 调用 _reconcileColumns
- **THEN** 执行 ALTER TABLE ADD COLUMN 添加 billing_provider

#### Scenario: 不添加已存在的列
- **GIVEN** 数据库包含所有声明的列
- **WHEN** 调用 _reconcileColumns
- **THEN** 不执行任何 ALTER TABLE 操作

#### Scenario: 处理重复列错误
- **GIVEN** 数据库已包含某列，但 SCHEMA_SQL 也声明了该列
- **WHEN** 调用 _reconcileColumns
- **THEN** 捕获 "duplicate column name" 错误，不抛出

### Requirement: 延迟索引创建 SHALL 在协调之后
测试 SHALL 验证依赖新列的索引在协调之后创建。

#### Scenario: 协调后创建索引
- **GIVEN** 索引 WHERE 子句引用协调添加的列
- **WHEN** 初始化 SessionDB
- **THEN** 索引在 _reconcileColumns 之后创建

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
