## ADDED Requirements

### Requirement: 系统 SHALL 使用声明式 schema 协调
系统 SHALL 以 SCHEMA_SQL 为唯一真实来源。启动时，系统 SHALL 对比 live 表和声明表的列，自动添加缺失列。

**设计理由：** 添加新列只需修改 SCHEMA_SQL，下次启动时自动协调。不需要版本控制的迁移代码。

#### Scenario: 解析期望列
- **WHEN** SessionDB 初始化时
- **THEN** 使用内存 SQLite 数据库解析 SCHEMA_SQL，提取每个表的期望列

#### Scenario: 添加缺失列
- **WHEN** live 表缺少声明的列
- **THEN** 执行 ALTER TABLE ADD COLUMN 添加缺失列

### Requirement: 声明式协调 SHALL 处理列类型重建
系统 SHALL 从 PRAGMA table_info 重建列类型表达式，包含类型、NOT NULL 约束、DEFAULT 值。

#### Scenario: 重建列类型
- **WHEN** 列有类型 "TEXT NOT NULL DEFAULT ''"
- **THEN** ALTER TABLE ADD COLUMN 使用完整类型表达式

### Requirement: 索引创建 SHALL 在协调之后
依赖协调添加列的索引 SHALL 在 _reconcile_columns 之后创建，避免在遗留数据库上因列不存在而失败。

#### Scenario: 延迟索引创建
- **WHEN** 索引的 WHERE 子句引用协调添加的列
- **THEN** 索引在协调之后创建，使用 CREATE INDEX IF NOT EXISTS

### Requirement: schema_version 表 SHALL 保留用于数据迁移
系统 SHALL 保留 schema_version 表，用于未来无法用声明式协调处理的数据迁移（行转换）。

#### Scenario: 版本跟踪
- **WHEN** 数据库初始化时
- **THEN** 更新 schema_version 表到当前 SCHEMA_VERSION

#### Scenario: 版本门控迁移
- **WHEN** 当前版本低于迁移目标版本
- **THEN** 执行版本门控的数据迁移代码
