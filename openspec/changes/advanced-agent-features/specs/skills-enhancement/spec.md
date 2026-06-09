## ADDED Requirements

### Requirement: Shell command execution in skill prompts
系统 SHALL 支持在 SKILL.md 内容中嵌入 Shell 命令，语法为 `` !`command` ``（内联）或 ```` ```!\ncommand\n``` ````（代码块）。技能被调用时，嵌入的命令先在宿主机执行，输出替换回 Markdown 正文。

#### Scenario: 内联 Shell 命令执行
- **WHEN** SKILL.md 包含 `` 当前分支：!`git branch --show-current` ``
- **THEN** 技能被调用时，系统 SHALL 执行 `git branch --show-current`，将输出替换到 Markdown 中

#### Scenario: Shell 命令走统一权限系统
- **WHEN** 技能中的 Shell 命令需要执行
- **THEN** 系统 SHALL 通过 hasPermissionsToUseTool 检查权限，拒绝未授权的命令

### Requirement: MCP source shell execution block
系统 SHALL 阻止来自 MCP Server 的技能执行内嵌 Shell 命令，防止远程代码执行（RCE）攻击。

#### Scenario: MCP 来源技能跳过 Shell 执行
- **WHEN** 技能的 loadedFrom 为 'mcp'
- **THEN** 系统 SHALL 跳过所有内嵌 Shell 命令的执行，保留原始文本

### Requirement: Conditional skill activation via paths
系统 SHALL 支持 SKILL.md frontmatter 中的 `paths` 字段（glob pattern 列表）。当用户操作或修改了匹配该 pattern 的文件时，技能自动激活并注入上下文。

#### Scenario: 文件变更触发条件技能
- **WHEN** 用户编辑了 `src/components/Button.tsx` 且某技能的 `paths` 包含 `src/components/**/*.tsx`
- **THEN** 该技能 SHALL 自动激活，其 prompt 内容被注入到下一轮对话上下文

#### Scenario: 未匹配的技能不激活
- **WHEN** 用户编辑了 `README.md` 且技能的 `paths` 不包含 `*.md`
- **THEN** 该技能 SHALL 保持未激活状态

### Requirement: Built-in variable substitution
系统 SHALL 在技能 prompt 中支持内置变量替换：`${CLAUDE_SKILL_DIR}` 替换为技能目录路径，`${CLAUDE_SESSION_ID}` 替换为当前会话 ID。

#### Scenario: 技能目录变量替换
- **WHEN** SKILL.md 包含 `${CLAUDE_SKILL_DIR}/templates/config.yaml`
- **THEN** 系统 SHALL 将 `${CLAUDE_SKILL_DIR}` 替换为技能所在的绝对路径
