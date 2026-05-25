## ADDED Requirements

### Requirement: 技能捆绑加载 SHALL 正确工作
测试 SHALL 验证捆绑解析和优先级。

#### Scenario: 加载捆绑
- **GIVEN** 捆绑 YAML 文件包含 skills: ['skill-a', 'skill-b']
- **WHEN** 调用加载捆绑
- **THEN** 返回两个技能的内容

#### Scenario: 捆绑优先于技能
- **GIVEN** 捆绑和技能同名 'research'
- **WHEN** 调用 /research
- **THEN** 加载捆绑而非技能
