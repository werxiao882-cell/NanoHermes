## ADDED Requirements

### Requirement: 上下文文件扫描 SHALL 检测注入
测试 SHALL 验证威胁模式检测。

#### Scenario: 检测 "ignore previous instructions"
- **GIVEN** 上下文文件包含 "Ignore all previous instructions"
- **WHEN** 调用 scanContextContent
- **THEN** 返回 BLOCKED 消息
- **AND** 记录警告日志

#### Scenario: 检测不可见 Unicode
- **GIVEN** 上下文文件包含零宽字符 \u200b
- **WHEN** 调用 scanContextContent
- **THEN** 返回 BLOCKED 消息
- **AND** 包含 "invisible unicode U+200B"

#### Scenario: 检测 curl 密钥泄露
- **GIVEN** 上下文文件包含 'curl -H "Authorization: $API_KEY"'
- **WHEN** 调用 scanContextContent
- **THEN** 返回 BLOCKED 消息
- **AND** 包含 "exfil_curl"

#### Scenario: 安全内容通过
- **GIVEN** 上下文文件包含安全内容
- **WHEN** 调用 scanContextContent
- **THEN** 返回原始内容
