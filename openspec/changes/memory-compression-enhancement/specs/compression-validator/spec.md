## ADDED Requirements

### Requirement: 信息保留度验证
系统 SHALL 验证压缩后的信息保留度。

#### Scenario: 保留度达标
- **WHEN** 原始消息和摘要的关键词 Jaccard 相似度 >= 0.6
- **THEN** `validate()` 返回 `is_valid=True`
- **AND** `retention_rate` >= 0.6

#### Scenario: 保留度不达标
- **WHEN** 原始消息和摘要的关键词 Jaccard 相似度 < 0.6
- **THEN** `validate()` 返回 `is_valid=False`
- **AND** `warnings` 包含 "Low information retention"

#### Scenario: 自定义保留度阈值
- **WHEN** 初始化时指定 `min_retention_rate=0.7`
- **THEN** 保留度 >= 0.7 时判定为达标

### Requirement: 摘要长度验证
系统 SHALL 验证摘要长度是否在合理范围内。

#### Scenario: 摘要长度达标
- **WHEN** 摘要长度 >= 500 且 <= 12000 字符
- **THEN** `validate()` 返回 `is_valid=True`
- **AND** `summary_length` 在合理范围内

#### Scenario: 摘要过短
- **WHEN** 摘要长度 < 500 字符
- **THEN** `validate()` 返回 `is_valid=False`
- **AND** `warnings` 包含 "Summary too short"

#### Scenario: 摘要过长
- **WHEN** 摘要长度 > 12000 字符
- **THEN** `validate()` 返回 `is_valid=False`
- **AND** `warnings` 包含 "Summary too long"

#### Scenario: 自定义长度阈值
- **WHEN** 初始化时指定 `min_summary_length=300` 和 `max_summary_length=15000`
- **THEN** 使用自定义阈值进行验证

### Requirement: 关键信息完整性验证
系统 SHALL 验证摘要是否包含关键信息。

#### Scenario: 包含文件变更信息
- **WHEN** 原始消息包含文件操作且摘要包含 "file"、"修改" 或 "create"
- **THEN** `has_file_changes` 返回 `True`

#### Scenario: 包含用户意图
- **WHEN** 压缩后消息的最后 5 条包含用户消息
- **THEN** `has_user_intent` 返回 `True`

#### Scenario: 包含工具调用信息
- **WHEN** 原始消息包含工具调用且摘要包含 "tool" 或 "function"
- **THEN** `has_tool_calls` 返回 `True`

### Requirement: 验证结果结构
系统 SHALL 返回结构化的验证结果。

#### Scenario: 验证结果包含所有字段
- **WHEN** 调用 `validate()` 方法
- **THEN** 返回字典包含：
  - `is_valid`: 布尔值，表示验证是否通过
  - `retention_rate`: 浮点数，信息保留率
  - `summary_length`: 整数，摘要长度
  - `has_file_changes`: 布尔值，是否包含文件变更
  - `has_user_intent`: 布尔值，是否包含用户意图
  - `has_tool_calls`: 布尔值，是否包含工具调用
  - `warnings`: 列表，警告信息

#### Scenario: 验证通过无警告
- **WHEN** 所有验证项都达标
- **THEN** `is_valid=True`
- **AND** `warnings` 为空列表

#### Scenario: 验证失败包含警告
- **WHEN** 至少一个验证项不达标
- **THEN** `is_valid=False`
- **AND** `warnings` 包含具体的警告信息

### Requirement: 验证器配置
系统 SHALL 支持可配置的验证参数。

#### Scenario: 自定义验证参数
- **WHEN** 初始化时指定：
  - `min_retention_rate=0.7`
  - `min_summary_length=300`
  - `max_summary_length=15000`
- **THEN** 使用自定义参数进行验证

#### Scenario: 默认验证参数
- **WHEN** 未指定验证参数
- **THEN** 使用默认值：
  - `min_retention_rate=0.6`
  - `min_summary_length=500`
  - `max_summary_length=12000`

### Requirement: 关键词提取
系统 SHALL 提供关键词提取功能用于信息保留度计算。

#### Scenario: 提取英文关键词
- **WHEN** 输入文本 "The user wants to create a new file"
- **THEN** 提取关键词集合包含 "user"、"create"、"file"

#### Scenario: 提取中文关键词
- **WHEN** 输入文本 "用户想要创建一个新文件"
- **THEN** 提取关键词集合包含 "用户"、"创建"、"文件"

#### Scenario: 过滤停用词
- **WHEN** 输入文本包含常见停用词（如 "the"、"a"、"is"）
- **THEN** 关键词集合不包含停用词

#### Scenario: 空文本处理
- **WHEN** 输入空文本
- **THEN** 返回空集合
