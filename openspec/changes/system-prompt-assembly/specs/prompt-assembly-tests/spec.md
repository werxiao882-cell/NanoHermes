## ADDED Requirements

### Requirement: 三层提示组装 SHALL 正确工作
测试 SHALL 验证 stable/context/volatile 层构建。

#### Scenario: 构建完整提示
- **GIVEN** Agent 状态包含所有组件
- **WHEN** 调用 buildSystemPromptParts
- **THEN** stable 层包含身份、工具指导、技能提示
- **AND** context 层包含上下文文件和 system_message
- **AND** volatile 层包含记忆快照和用户画像

#### Scenario: 缓存提示
- **GIVEN** Agent 状态，已构建提示
- **WHEN** 再次调用 buildSystemPromptParts
- **THEN** 返回缓存的提示

#### Scenario: 压缩后重建
- **GIVEN** Agent 状态，提示已缓存
- **WHEN** 上下文压缩触发
- **THEN** 提示被重建
