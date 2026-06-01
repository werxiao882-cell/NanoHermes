## ADDED Requirements

### Requirement: 系统 SHALL 提供辅助 LLM 客户端
系统 SHALL 提供 AuxiliaryClient 类，用于压缩等后台任务。客户端 SHALL 支持自动提供商解析和连接错误处理。

#### Scenario: 解析辅助提供商
- **WHEN** 配置为 "auto" 时
- **THEN** 客户端从主提供商解析辅助提供商

#### Scenario: 处理连接错误
- **WHEN** 辅助 LLM 调用遇到连接错误
- **THEN** 客户端重试或回退到默认提供商

### Requirement: 辅助客户端 SHALL 与主客户端隔离
辅助客户端 SHALL 使用独立的 API 调用，不影响主会话的提示缓存。

#### Scenario: 独立 API 调用
- **WHEN** 辅助客户端调用 LLM
- **THEN** 主会话的提示缓存不受影响

### Requirement: 辅助客户端 SHALL 支持可行性检查
系统 SHALL 提供 check_compression_model_feasibility 方法，验证辅助模型上下文窗口是否满足压缩要求。

**检查逻辑：**
1. 如果辅助模型上下文窗口 < MINIMUM_CONTEXT_LENGTH，返回不可行
2. 如果辅助模型上下文窗口 < 主模型压缩阈值（80%），返回可行但有警告
3. 否则返回可行

#### Scenario: 辅助模型窗口太小
- **WHEN** 辅助模型上下文窗口小于最小要求
- **THEN** 返回不可行，包含原因说明

#### Scenario: 辅助模型窗口小于主模型阈值
- **WHEN** 辅助模型上下文窗口小于主模型压缩阈值（80%）
- **THEN** 返回可行，但包含警告

#### Scenario: 可行配置
- **WHEN** 辅助模型上下文窗口满足要求
- **THEN** 返回可行
