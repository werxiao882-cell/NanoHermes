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
