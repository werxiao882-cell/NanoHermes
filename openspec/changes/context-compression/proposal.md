## 为什么

业界成熟的自进化 AI Agent 系统使用辅助 LLM 模型自动压缩长对话的上下文，将中间轮次摘要化，同时保护头部和尾部上下文。这使 Agent 能够处理超出模型上下文窗口的长对话。NanoHermes 需要实现相同的上下文压缩机制。

**为什么长对话是个工程问题：** LLM 上下文窗口有限（128K-200K tokens），30 次工具调用可能消耗 80K+ tokens，超限会返回 `context_length_exceeded` 错误。

**设计赌注回扣：** 上下文压缩服务于 **Personal Long-Term**（通过 `on_pre_compress` 钩子在压缩前保存记忆，确保长对话中的重要信息不丢失）和 **Run Anywhere**（压缩后的 session splitting 让 SQLite 写入保持小事务，减少 WAL 锁竞争）。

## 变更内容

- 实现 ContextEngine 抽象基类（可插拔扩展点）
- 实现上下文窗口使用率检测（预飞行 + 响应后）
- 实现辅助 LLM 客户端配置和可行性检查
- 实现结构化摘要生成（目标、进展、关键决策、修改文件、下一步）
- 实现头部和尾部上下文保护（情景记忆理论）
- 实现工具输出剪枝和参数截断（保持 JSON 有效性）
- 实现迭代摘要更新（保持多次压缩后的连贯性）
- 实现压缩后的会话分割和 ID 轮换（Session Splitting + parent_session_id 血缘链）
- 实现 `on_pre_compress` 钩子通知 Memory Provider 提取信息

## 能力

### 新增能力

- `context-engine-interface`: ContextEngine 抽象基类，定义可插拔上下文引擎接口。包含 3 个核心抽象方法（`update_from_response`, `should_compress`, `compress`）和可选工具接口。第三方引擎（如 LCM、自定义摘要引擎）可通过配置 `context.engine` 替换内置压缩器。
- `context-compressor`: 上下文压缩引擎，实现分层压缩策略：Tool Output Pruning → Head/Tail 保护 → Middle 摘要 → Session Splitting。检测上下文窗口使用率，使用辅助 LLM 生成结构化摘要，保护头部和尾部上下文。摘要预算按比例缩放（20%），最小 2000 token，最大 12000 token。
- `auxiliary-client`: 辅助 LLM 客户端，用于压缩等后台任务。支持自动提供商解析和连接错误处理。
- `tool-output-pruning`: 工具输出剪枝，在发送给 LLM 摘要器之前剪枝旧工具输出（>200 字符替换为占位符）、截断长工具调用参数（解析 JSON 后截断字符串叶子节点，保持 JSON 有效性）。
- `session-splitting`: 压缩触发时创建新 session，`parent_session_id` 指向旧 session（建立血缘链），摘要作为新 session 第一条消息，尾部保护消息搬到新 session。
- `on-pre-compress-hook`: 压缩前通知 Memory Provider 提取有价值信息（如 Honcho 提取用户偏好变更），确保信息不丢失。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/compression/` 目录，包含 `context_engine.py`、`context_compressor.py`
- 依赖辅助 LLM 提供商配置
- 压缩触发时会分割会话并轮换 session_id（通过 SessionDB 的 `parent_session_id` 建立血缘链）
- 无破坏性变更，从零开始构建
- 预留外部 ContextEngine 插件接口（LCM、自定义摘要引擎）
