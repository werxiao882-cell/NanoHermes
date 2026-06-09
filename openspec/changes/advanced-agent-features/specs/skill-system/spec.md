## MODIFIED Requirements

### Requirement: Skill shell execution support
SkillManager SHALL 扩展支持 SKILL.md 中的内嵌 Shell 命令执行。在技能被调用时，先执行嵌入的 Shell 命令（`` !`command` `` 语法），将输出替换到 Markdown 正文后再注入上下文。MCP 来源的技能 SHALL 跳过 Shell 执行。

#### Scenario: 技能中的 Shell 命令被执行
- **WHEN** 技能 SKILL.md 包含 `` !`git status --short` `` 且 loadedFrom 不是 'mcp'
- **THEN** SkillManager SHALL 执行该命令并将输出替换到 prompt 中

#### Scenario: MCP 来源技能跳过 Shell
- **WHEN** 技能的 loadedFrom 为 'mcp'
- **THEN** SkillManager SHALL 跳过所有内嵌 Shell 命令的执行

### Requirement: Conditional skill activation
SkillManager SHALL 支持条件技能：SKILL.md frontmatter 中的 `paths` 字段声明 glob pattern 列表。当文件变更匹配 pattern 时，技能自动激活。

#### Scenario: 文件变更触发条件技能激活
- **WHEN** 用户编辑了匹配某技能 `paths` 的文件
- **THEN** 该技能 SHALL 自动激活，其 prompt 被注入下一轮对话上下文

### Requirement: Skill discovery memoization
SkillManager 的技能发现 SHALL 使用 memoize 缓存，同一 cwd 只扫描一次。后续调用返回缓存结果。

#### Scenario: 重复调用使用缓存
- **WHEN** `get_skill_commands()` 被调用两次且 cwd 未变
- **THEN** 第二次调用 SHALL 返回缓存结果，不重新扫描文件系统
