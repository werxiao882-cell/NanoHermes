## ADDED Requirements

### Requirement: AuxiliaryClient 解析提供商 SHALL 正确工作
测试 SHALL 验证提供商解析逻辑。

#### Scenario: 解析 auto 提供商
- **GIVEN** 配置 compression.provider='auto'
- **WHEN** 调用 resolveAuxModel('compression')
- **THEN** 从主提供商解析辅助提供商

#### Scenario: 解析明确提供商
- **GIVEN** 配置 compression.provider='openrouter'
- **WHEN** 调用 resolveAuxModel('compression')
- **THEN** 返回 openrouter 提供商

### Requirement: AuxiliaryClient 处理连接错误 SHALL 重试
测试 SHALL 验证连接错误处理。

#### Scenario: 连接错误重试
- **GIVEN** AuxiliaryClient 实例
- **WHEN** API 调用遇到连接错误
- **THEN** 重试或回退到默认提供商
