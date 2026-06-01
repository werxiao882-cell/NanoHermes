## ADDED Requirements

### Requirement: ContextEngine 抽象基类 SHALL 正确定义接口
测试 SHALL 验证抽象类的方法和默认实现。

#### Scenario: 无法实例化抽象类
- **GIVEN** ContextEngine 抽象类
- **WHEN** 尝试直接实例化
- **THEN** 抛出 TypeError

#### Scenario: 具体实现可以实例化
- **GIVEN** 实现所有核心抽象方法的具体类
- **WHEN** 实例化
- **THEN** 成功创建实例

#### Scenario: 默认工具接口返回空
- **GIVEN** 具体 ContextEngine 实现
- **WHEN** 调用 get_tool_schemas
- **THEN** 返回空列表

### Requirement: compress 方法 SHALL 压缩上下文
测试 SHALL 验证头部/尾部保护和摘要生成。

#### Scenario: 压缩长对话
- **GIVEN** ContextCompressor 实例，100 条消息
- **WHEN** 调用 compress
- **THEN** 返回头部消息 + 摘要系统消息 + 尾部消息
- **AND** 头部消息数量正确（前 3 条）
- **AND** 尾部消息在 token 预算内

#### Scenario: 摘要包含正确前缀
- **GIVEN** ContextCompressor 实例
- **WHEN** 调用 compress
- **THEN** 摘要消息包含 '[CONTEXT COMPACTION — REFERENCE ONLY]' 前缀

#### Scenario: 迭代摘要更新
- **GIVEN** ContextCompressor 实例，已有 _previous_summary
- **WHEN** 调用 compress
- **THEN** 摘要提示包含前次摘要内容
- **AND** 新信息与旧信息合并

#### Scenario: 首次摘要生成
- **GIVEN** ContextCompressor 实例，_previous_summary 为 None
- **WHEN** 调用 compress
- **THEN** 摘要提示不包含前次摘要内容

### Requirement: calculate_summary_budget 方法 SHALL 按比例计算预算
测试 SHALL 验证预算计算逻辑。

#### Scenario: 小内容预算
- **GIVEN** 压缩内容 10000 字符
- **WHEN** 调用 calculate_summary_budget
- **THEN** 返回 2000（最小值）

#### Scenario: 中等内容预算
- **GIVEN** 压缩内容 50000 字符
- **WHEN** 调用 calculate_summary_budget
- **THEN** 返回 2500（50000 * 0.20 / 4）

#### Scenario: 大内容预算上限
- **GIVEN** 压缩内容 500000 字符
- **WHEN** 调用 calculate_summary_budget
- **THEN** 返回 12000（最大值）

### Requirement: protect_head 方法 SHALL 保护前 N 条消息
测试 SHALL 验证头部保护。

#### Scenario: 保护前 3 条消息
- **GIVEN** 10 条消息
- **WHEN** 调用 protect_head
- **THEN** 返回前 3 条消息

#### Scenario: 消息少于保护数量
- **GIVEN** 2 条消息
- **WHEN** 调用 protect_head
- **THEN** 返回所有 2 条消息

### Requirement: protect_tail 方法 SHALL 使用 token 预算保护尾部
测试 SHALL 验证尾部保护。

#### Scenario: 保护尾部消息
- **GIVEN** 10 条消息，contextLength=8000
- **WHEN** 调用 protect_tail
- **THEN** 返回尾部消息，总 token 数不超过 2000（8000 * 0.25）

### Requirement: Session Splitting SHALL 创建新会话
测试 SHALL 验证压缩后会话分割。

#### Scenario: 新 session 创建
- **GIVEN** 压缩完成
- **WHEN** 调用 session_splitting
- **THEN** 创建新会话，parent_session_id 指向原始会话

#### Scenario: 摘要作为第一条消息
- **GIVEN** 新 session 创建
- **WHEN** 检查新 session 消息
- **THEN** 第一条消息包含压缩摘要文本

#### Scenario: 尾部消息迁移
- **GIVEN** 新 session 创建
- **WHEN** 检查新 session 消息
- **THEN** 尾部保护的消息被搬到新 session

### Requirement: on_pre_compress 钩子 SHALL 在压缩前调用
测试 SHALL 验证钩子调用时机。

#### Scenario: 钩子在压缩前调用
- **GIVEN** MemoryManager 注册了 Provider
- **WHEN** 压缩即将开始
- **THEN** 调用所有 Provider 的 on_pre_compress 方法

#### Scenario: Provider 提取信息
- **GIVEN** Provider 实现了 on_pre_compress
- **WHEN** 钩子被调用
- **THEN** Provider 可以从即将被压缩的消息中提取信息

#### Scenario: 钩子失败不影响压缩
- **GIVEN** Provider 的 on_pre_compress 抛出异常
- **WHEN** 压缩开始
- **THEN** 记录警告，压缩继续进行
