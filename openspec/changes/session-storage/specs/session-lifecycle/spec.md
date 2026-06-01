## ADDED Requirements

### Requirement: 系统 SHALL 支持会话创建
系统 SHALL 提供 create_session 方法，接受 session_id、source、model 等参数，插入新会话记录。

#### Scenario: 创建新会话
- **WHEN** 用户开始新对话
- **THEN** 创建包含 id、source、model、started_at 的会话记录

#### Scenario: 幂等创建
- **WHEN** 相同的 session_id 被创建多次
- **THEN** 使用 INSERT OR IGNORE，第二次创建不产生错误

### Requirement: 系统 SHALL 支持会话结束和恢复
系统 SHALL 提供 end_session 方法标记会话结束，提供 reopen_session 方法清除 ended_at/end_reason 以便恢复。

#### Scenario: 结束会话
- **WHEN** 用户退出或会话超时
- **THEN** 设置 ended_at 为当前时间，end_reason 为退出原因

#### Scenario: 恢复会话
- **WHEN** 用户使用 /resume 命令
- **THEN** 清除 ended_at 和 end_reason，使会话可以继续使用

### Requirement: 系统 SHALL 支持 parent_session_id lineage 追踪
系统 SHALL 通过 parent_session_id 外键追踪会话 lineage。压缩延续、委托子 agent、分支子节点 SHALL 设置 parent_session_id。

**设计理由：** parent_session_id 形成一条血缘链——当上下文压缩触发 session splitting 时，Hermes 创建一个新 session，将压缩后的消息写入新 session，并通过 parent_session_id 链接到旧 session。用户可以追溯一次长对话的完整历史。

#### Scenario: 压缩延续 lineage
- **WHEN** 会话被压缩并继续
- **THEN** 新会话的 parent_session_id 指向原会话

#### Scenario: 委托子 agent lineage
- **WHEN** 父 agent 委托任务给子 agent
- **THEN** 子 agent 会话的 parent_session_id 指向父会话

### Requirement: 系统 SHALL 区分压缩延续和其他子节点
系统 SHALL 通过 started_at >= parent.ended_at AND parent.end_reason = 'compression' 条件区分压缩延续和委托/分支子节点。

#### Scenario: 识别压缩延续
- **WHEN** 查找会话的压缩延续链
- **THEN** 只返回 parent_session_id 指向已结束（end_reason='compression'）会话，且 started_at >= parent.ended_at 的会话

#### Scenario: 排除委托子节点
- **WHEN** 查找压缩延续时
- **THEN** 委托子节点（在父会话还活着时创建）不被识别为压缩延续
