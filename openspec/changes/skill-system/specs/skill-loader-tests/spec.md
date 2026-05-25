## ADDED Requirements

### Requirement: SkillLoader 解析 SKILL.md SHALL 正确工作
测试 SHALL 验证 frontmatter 解析和验证。

#### Scenario: 解析有效 SKILL.md
- **GIVEN** SKILL.md 包含完整 frontmatter
- **WHEN** 调用 load
- **THEN** 返回包含 frontmatter 和 body 的 Skill 对象
- **AND** slug 正确生成

#### Scenario: description 超过 60 字符
- **GIVEN** SKILL.md 的 description 为 70 字符
- **WHEN** 调用 load
- **THEN** 记录警告日志
- **AND** 仍然返回 Skill 对象

#### Scenario: 缺少 frontmatter
- **GIVEN** SKILL.md 没有 frontmatter
- **WHEN** 调用 load
- **THEN** 抛出错误

#### Scenario: slugify 特殊字符
- **WHEN** slugify('My Cool Skill!')
- **THEN** 返回 'my-cool-skill'
