## ADDED Requirements

### Requirement: AuxiliaryClient  SHALL 解析辅助提供商
测试 SHALL 验证提供商解析逻辑。

#### Scenario: 解析 auto 提供商
- **GIVEN** 配置为 "auto"
- **WHEN** 解析辅助提供商
- **THEN** 从主提供商解析辅助提供商

#### Scenario: 解析明确提供商
- **GIVEN** 配置为明确的提供商名称
- **WHEN** 解析辅助提供商
- **THEN** 返回配置的提供商

### Requirement: AuxiliaryClient SHALL 处理连接错误
测试 SHALL 验证连接错误处理。

#### Scenario: 连接错误重试
- **GIVEN** 辅助 LLM 调用遇到连接错误
- **WHEN** 重试逻辑触发
- **THEN** 客户端重试或回退到默认提供商

### Requirement: check_compression_model_feasibility SHALL 验证辅助模型
测试 SHALL 验证辅助模型上下文窗口检查。

#### Scenario: 辅助模型窗口太小
- **GIVEN** 辅助模型上下文窗口小于 MINIMUM_CONTEXT_LENGTH
- **WHEN** 调用 check_compression_model_feasibility
- **THEN** 返回 feasible=False，包含原因说明

#### Scenario: 辅助模型窗口小于主模型阈值
- **GIVEN** 辅助模型上下文窗口小于主模型压缩阈值（80%）
- **WHEN** 调用 check_compression_model_feasibility
- **THEN** 返回 feasible=True，包含警告

#### Scenario: 可行配置
- **GIVEN** 辅助模型上下文窗口满足要求
- **WHEN** 调用 check_compression_model_feasibility
- **THEN** 返回 feasible=True
