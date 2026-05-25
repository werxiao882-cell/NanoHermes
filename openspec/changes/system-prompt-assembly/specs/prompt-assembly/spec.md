## ADDED Requirements

### Requirement: 系统 SHALL 使用三层提示组装
系统提示 SHALL 由三层组成：stable（身份、工具指导、技能提示）、context（上下文文件、system_message）、volatile（记忆快照、用户画像、元数据）。三层 SHALL 用 \n\n 连接。

#### Scenario: 构建三层提示
- **WHEN** 系统提示组装时
- **THEN** stable、context、volatile 三层分别构建并连接

#### Scenario: 缓存系统提示
- **WHEN** 会话期间
- **THEN** 系统提示被缓存，仅压缩时重建
