## ADDED Requirements

### Requirement: 系统 SHALL 扫描上下文文件的提示注入
系统 SHALL 在注入 AGENTS.md、.cursorrules、SOUL.md 等上下文文件之前扫描内容。检查 SHALL 包括不可见 Unicode 字符和威胁模式正则表达式。

#### Scenario: 检测提示注入
- **WHEN** 上下文文件包含 "ignore previous instructions" 模式
- **THEN** 文件被阻止，返回 BLOCKED 消息

#### Scenario: 检测不可见 Unicode
- **WHEN** 上下文文件包含零宽字符
- **THEN** 文件被阻止，记录发现的 Unicode 码位
