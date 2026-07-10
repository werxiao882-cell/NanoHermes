## ContextCompressor 核心实现

### 需求

- **MUST** 实现分层压缩策略：Tool Output Pruning → Head/Tail 保护 → Middle 摘要 → Session Splitting
- **MUST** 摘要预算按比例缩放（20%），最小 2000 token，最大 12000 token
- **MUST** 保护前 3 条消息和最后 20 条消息
- **MUST** 使用辅助 LLM 生成结构化摘要（目标、进展、关键决策、修改文件、下一步）
- **MUST** 实现迭代摘要更新（保持多次压缩后的连贯性）
- **MUST** 支持预飞行和响应后两种触发时机
