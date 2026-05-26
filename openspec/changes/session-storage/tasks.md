## 1. 项目设置

- [ ] 1.1 安装 better-sqlite3 依赖
- [ ] 1.2 创建 `src/session/` 目录结构
- [ ] 1.3 配置 TypeScript 编译选项
- [ ] 1.4 配置 vitest 测试框架

## 2. SessionDB 核心实现

- [ ] 2.1 实现 SessionDB 类构造函数，包含数据库连接和目录创建
- [ ] 2.2 实现 applyWalWithFallback 方法，包含 WAL 模式设置和 NFS/SMB 回退
- [ ] 2.3 实现 SCHEMA_SQL 常量，包含 sessions、messages、state_meta 表定义
- [ ] 2.4 实现 initSchema 方法，执行 schema 创建
- [ ] 2.5 实现 _executeWrite 方法，包含 BEGIN IMMEDIATE + 抖动重试逻辑
- [ ] 2.6 实现 _tryWalCheckpoint 方法，定期执行 PASSIVE checkpoint
- [ ] 2.7 实现 close 方法，包含最终 checkpoint 和连接关闭
- [ ] 2.8 编写 SessionDB 初始化和 WAL 模式的单元测试
  - [ ] 2.8.1 测试创建新数据库
  - [ ] 2.8.2 测试打开已存在的数据库
  - [ ] 2.8.3 测试 WAL 模式设置
  - [ ] 2.8.4 测试 WAL 回退到 DELETE 模式
  - [ ] 2.8.5 测试外键约束启用
  - [ ] 2.8.6 测试 _executeWrite 成功写入无竞争
  - [ ] 2.8.7 测试锁竞争重试成功
  - [ ] 2.8.8 测试达到最大重试次数
  - [ ] 2.8.9 测试非锁定错误立即传播
  - [ ] 2.8.10 测试定期 checkpoint
  - [ ] 2.8.11 测试 checkpoint 失败不抛出异常
  - [ ] 2.8.12 测试正常关闭
  - [ ] 2.8.13 测试重复关闭

## 3. FTS5 搜索实现

- [ ] 3.1 实现 FTS_SQL 常量，包含 messages_fts 虚拟表和触发器
- [ ] 3.2 实现 FTS_TRIGRAM_SQL 常量，包含 trigram 分词器虚拟表和触发器
- [ ] 3.3 在 initSchema 中创建 FTS 虚拟表和触发器
- [ ] 3.4 实现 searchMessages 方法，支持关键词搜索和会话过滤
- [ ] 3.5 编写 FTS 搜索的单元测试，包含 CJK 子串搜索
  - [ ] 3.5.1 测试创建标准 FTS5 表
  - [ ] 3.5.2 测试创建 trigram FTS5 表
  - [ ] 3.5.3 测试插入消息同步到 FTS
  - [ ] 3.5.4 测试删除消息同步到 FTS
  - [ ] 3.5.5 测试更新消息同步到 FTS
  - [ ] 3.5.6 测试搜索所有会话
  - [ ] 3.5.7 测试按会话过滤搜索
  - [ ] 3.5.8 测试搜索无结果
  - [ ] 3.5.9 测试中文子串搜索
  - [ ] 3.5.10 测试日文子串搜索
  - [ ] 3.5.11 测试混合语言搜索
  - [ ] 3.5.12 测试搜索工具名称
  - [ ] 3.5.13 测试搜索工具调用参数

## 4. 声明式 Schema 协调

- [ ] 4.1 实现 _parseSchemaColumns 方法，使用内存 SQLite 解析期望列
- [ ] 4.2 实现 _reconcileColumns 方法，对比 live 列和期望列
- [ ] 4.3 实现列类型表达式重建逻辑
- [ ] 4.4 实现延迟索引创建，在协调之后创建依赖新列的索引
- [ ] 4.5 编写 schema 协调的单元测试
  - [ ] 4.5.1 测试解析单表列
  - [ ] 4.5.2 测试解析多表列
  - [ ] 4.5.3 测试解析带 DEFAULT 的列
  - [ ] 4.5.4 测试添加缺失列
  - [ ] 4.5.5 测试不添加已存在的列
  - [ ] 4.5.6 测试处理重复列错误
  - [ ] 4.5.7 测试协调后创建索引
  - [ ] 4.5.8 测试索引创建失败不阻塞启动
  - [ ] 4.5.9 测试初始化 schema_version
  - [ ] 4.5.10 测试更新 schema_version

## 5. 会话生命周期管理

- [ ] 5.1 实现 createSession 方法
- [ ] 5.2 实现 endSession 方法，包含 ended_at 和 end_reason 设置
- [ ] 5.3 实现 reopenSession 方法，清除 ended_at 和 end_reason
- [ ] 5.4 实现 updateSystemPrompt 方法
- [ ] 5.5 实现 updateTokenCounts 方法，支持增量和绝对模式
- [ ] 5.6 实现 getSession 方法
- [ ] 5.7 实现 getCompressionTip 方法，walk 压缩延续链
- [ ] 5.8 编写会话生命周期的单元测试
  - [ ] 5.8.1 测试创建新会话
  - [ ] 5.8.2 测试幂等创建
  - [ ] 5.8.3 测试创建会话带完整参数
  - [ ] 5.8.4 测试结束会话
  - [ ] 5.8.5 测试已结束会话不重复结束
  - [ ] 5.8.6 测试恢复会话
  - [ ] 5.8.7 测试创建压缩延续会话
  - [ ] 5.8.8 测试获取压缩延续 tip
  - [ ] 5.8.9 测试排除委托子节点
  - [ ] 5.8.10 测试增量更新 token 计数
  - [ ] 5.8.11 测试绝对更新 token 计数
  - [ ] 5.8.12 测试更新模型信息
  - [ ] 5.8.13 测试获取存在的会话
  - [ ] 5.8.14 测试获取不存在的会话

## 6. 会话标题管理

- [ ] 6.1 创建唯一标题索引 idx_sessions_title_unique
- [ ] 6.2 实现 sanitizeTitle 方法，包含控制字符剥离和长度验证
- [ ] 6.3 实现 setSessionTitle 方法，包含唯一性检查
- [ ] 6.4 实现 getSessionTitle 方法
- [ ] 6.5 实现 resolveSessionByTitle 方法，支持精确匹配和编号变体
- [ ] 6.6 实现 getNextTitleInLineage 方法
- [ ] 6.7 编写标题管理的单元测试
  - [ ] 6.7.1 测试设置新标题
  - [ ] 6.7.2 测试标题唯一性检查
  - [ ] 6.7.3 测试更新自己的标题
  - [ ] 6.7.4 测试剥离控制字符
  - [ ] 6.7.5 测试折叠空白
  - [ ] 6.7.6 测试标题过长
  - [ ] 6.7.7 测试空标题
  - [ ] 6.7.8 测试精确标题匹配
  - [ ] 6.7.9 测试编号变体匹配
  - [ ] 6.7.10 测试标题不存在
  - [ ] 6.7.11 测试生成第一个编号标题
  - [ ] 6.7.12 测试生成后续编号标题
  - [ ] 6.7.13 测试剥离现有编号后缀

## 7. 集成测试

- [x] 7.1 编写 SessionDB 完整生命周期的集成测试
- [x] 7.2 编写并发写入的集成测试，验证抖动重试
- [x] 7.3 编写 FTS 搜索的集成测试，包含多会话搜索
- [x] 7.4 编写 schema 协调的集成测试，验证列添加
- [x] 7.5 编写完整工作流集成测试（创建会话 → 插入消息 → 搜索 → 结束 → 恢复）
- [x] 7.6 编写压缩延续链集成测试
- [x] 7.7 编写标题 lineage 集成测试

## 8. JSONL 会话历史存储

- [x] 8.1 实现 JsonlSessionStore 类，支持 JSONL 格式追加写入
- [x] 8.2 实现 append_message 方法，支持完整消息元数据（role, content, tool_calls, reasoning）
- [x] 8.3 实现 load_messages 方法，从 JSONL 文件加载完整历史
- [x] 8.4 实现 list_sessions 方法，列出所有有 JSONL 文件的会话
- [x] 8.5 实现 session_exists 和 delete_session 方法
- [x] 8.6 编写 JSONL 存储的单元测试
- [x] 8.7 实现 ConversationLoop on_message_append 回调，实时保存 tool 消息到 JSONL
- [x] 8.8 验证 JSONL 包含完整上下文（用户/助手/工具调用/工具结果）

## 9. 会话恢复命令

- [ ] 9.1 实现 --resume <session_id> 命令行参数
- [ ] 9.2 实现 --resume-title "title" 命令行参数
- [ ] 9.3 实现 --resume（无参数）恢复最近会话
- [ ] 9.4 实现恢复时加载 JSONL 历史并显示摘要
- [ ] 9.5 实现恢复失败时的错误处理和新建会话
- [ ] 9.6 编写会话恢复的集成测试
