## ADDED Requirements

### Requirement: 系统 SHALL 支持会话标题管理
系统 SHALL 提供 set_session_title、get_session_title 方法。标题 SHALL 唯一，通过唯一索引 idx_sessions_title_unique 强制执行。

#### Scenario: 设置会话标题
- **WHEN** 用户或系统设置会话标题
- **THEN** 更新 sessions 表的 title 字段

#### Scenario: 标题唯一性检查
- **WHEN** 设置的标题已被其他会话使用
- **THEN** 抛出错误，拒绝设置

### Requirement: 系统 SHALL 支持标题解析到会话 ID
系统 SHALL 提供 resolve_session_by_title 方法，优先返回 lineage 中最新的会话。

#### Scenario: 精确标题匹配
- **WHEN** 标题精确存在
- **THEN** 返回该会话的 ID

#### Scenario: 编号变体匹配
- **WHEN** 标题不存在但存在 "title #2"、"title #3" 等编号变体
- **THEN** 返回最新的编号变体的会话 ID

### Requirement: 系统 SHALL 生成 lineage 中的下一个标题
系统 SHALL 提供 get_next_title_in_lineage 方法，剥离现有 #N 后缀，找到最大编号，生成下一个编号标题。

#### Scenario: 生成下一个编号标题
- **WHEN** 基础标题 "my session" 已存在
- **THEN** 返回 "my session #2"

#### Scenario: 处理现有编号后缀
- **WHEN** 输入标题为 "my session #3"
- **THEN** 剥离后缀找到基础标题 "my session"，返回下一个编号 "my session #4"

### Requirement: 系统 SHALL 验证和清理标题
系统 SHALL 提供 sanitize_title 方法，剥离控制字符、折叠空白、限制最大长度（100 字符）。

#### Scenario: 清理标题
- **WHEN** 标题包含零宽字符或控制字符
- **THEN** 剥离这些字符，返回清理后的标题

#### Scenario: 标题长度限制
- **WHEN** 标题超过 100 字符
- **THEN** 抛出 ValueError 错误
