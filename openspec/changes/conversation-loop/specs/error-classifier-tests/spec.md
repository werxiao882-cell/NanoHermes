## ADDED Requirements

### Requirement: 错误分类器 SHALL 正确分类所有错误类型
测试 SHALL 验证每种错误类型的分类。

#### Scenario: 分类 401 认证错误
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { statusCode: 401, message: 'Unauthorized' }
- **THEN** reason=auth
- **AND** retryable=true
- **AND** shouldRotateCredential=true

#### Scenario: 分类 402 计费错误
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { statusCode: 402, message: 'Insufficient credits' }
- **THEN** reason=billing
- **AND** retryable=false
- **AND** shouldRotateCredential=true

#### Scenario: 分类 429 速率限制
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { statusCode: 429, message: 'Rate limit exceeded' }
- **THEN** reason=rateLimit
- **AND** retryable=true
- **AND** shouldRotateCredential=true

#### Scenario: 分类上下文溢出
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { message: 'maximum context length exceeded' }
- **THEN** reason=contextOverflow
- **AND** shouldCompress=true

#### Scenario: 分类服务器错误
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { statusCode: 500, message: 'Internal server error' }
- **THEN** reason=serverError
- **AND** retryable=true

#### Scenario: 分类未知错误
- **GIVEN** ErrorClassifier 实例
- **WHEN** 分类 { message: 'Unknown error' }
- **THEN** reason=unknown
- **AND** retryable=true
