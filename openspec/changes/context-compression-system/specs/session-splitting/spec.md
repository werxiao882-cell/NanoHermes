## Session Splitting

### 需求

- **MUST** 压缩触发时创建新 session
- **MUST** `parent_session_id` 指向旧 session（建立血缘链）
- **MUST** 摘要作为新 session 第一条消息
- **MUST** 尾部保护消息搬到新 session
