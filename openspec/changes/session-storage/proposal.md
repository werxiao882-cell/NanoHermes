## 为什么

业界成熟的自进化 AI Agent 系统使用 SQLite 作为所有会话数据的持久化存储，支持跨会话记忆检索、全文搜索、会话 lineage 追踪等核心功能。NanoHermes 需要实现相同的存储层，作为所有其他功能的基础设施。

## 变更内容

- 实现基于 SQLite 的会话数据库 (SessionDB)，支持 WAL 模式并发访问
- 创建 FTS5 全文搜索索引，支持跨会话消息检索
- 实现三字符分词 (trigram) 支持 CJK 子串搜索
- 实现会话生命周期管理：创建、结束、恢复、分支
- 实现会话标题管理和 lineage 追踪（压缩延续链）
- 实现声明式 schema 协调，支持无迁移的列添加

## 能力

### 新增能力

- `session-database`: SQLite 会话存储，包含 sessions 表、messages 表、state_meta 表。WAL 模式支持并发读取 + 单写入。应用层抖动重试处理写锁竞争。
- `fts5-search`: FTS5 全文搜索，包含标准 unicode61 分词器和 trigram 分词器。支持跨会话消息搜索、CJK 子串匹配。
- `session-lifecycle`: 会话生命周期管理，支持创建、结束、恢复、分支。parent_session_id 支持会话 lineage 追踪。
- `session-title`: 会话标题管理，支持唯一标题、标题解析、lineage 中最新会话解析、编号标题变体（如 "title #2"）。
- `schema-reconciliation`: 声明式 schema 协调，SCHEMA_SQL 是唯一真实来源。启动时对比 live 列和声明列，自动添加缺失列。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/session/` 目录，包含 SessionDB 类和 schema 定义
- 依赖 better-sqlite3 作为 SQLite 绑定
- 所有其他功能（记忆、压缩、委托等）都依赖此存储层
- 无破坏性变更，从零开始构建
