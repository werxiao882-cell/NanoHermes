## ADDED Requirements

### Requirement: 系统 SHALL 支持模板变量替换
技能预处理 SHALL 在加载 SKILL.md 时执行模板变量替换：
- `${HERMES_SKILL_DIR}`：替换为技能目录的绝对路径
- `${HERMES_SESSION_ID}`：替换为当前会话 ID
- `${HERMES_HOME}`：替换为 ~/.nanohermes 路径

#### Scenario: 替换技能目录变量
- **WHEN** SKILL.md 包含 `${HERMES_SKILL_DIR}/references/guide.md`
- **THEN** 替换为 `/path/to/skills/my-skill/references/guide.md`

#### Scenario: 替换会话 ID 变量
- **WHEN** SKILL.md 包含 `Session: ${HERMES_SESSION_ID}`
- **THEN** 替换为 `Session: abc123-def456`

### Requirement: 系统 SHALL 支持内联 shell 展开
技能预处理 SHALL 支持 `` `!`command`` `` 语法，执行 shell 命令并替换为输出结果。

#### Scenario: 展开简单命令
- **WHEN** SKILL.md 包含 `` `!`date +%Y-%m-%d`` ``
- **THEN** 替换为命令输出，如 `2026-06-13`

#### Scenario: 展开多行命令
- **WHEN** SKILL.md 包含 `` `!`ls -la ${HERMES_SKILL_DIR}`` ``
- **THEN** 替换为目录列表输出

### Requirement: 系统 SHALL 限制 shell 展开的安全性
内联 shell 展开 SHALL 有安全限制：
- 超时：5 秒
- 禁止危险命令：rm -rf /、mkfs、dd if=/dev/zero
- 禁止网络请求：curl、wget（防止数据泄露）

#### Scenario: 命令超时
- **WHEN** shell 命令执行超过 5 秒
- **THEN** 终止命令并替换为 `[Command timed out]`

#### Scenario: 检测到危险命令
- **WHEN** shell 命令包含 `rm -rf /`
- **THEN** 拒绝执行并替换为 `[Dangerous command blocked]`

#### Scenario: 检测到网络请求
- **WHEN** shell 命令包含 `curl` 或 `wget`
- **THEN** 拒绝执行并替换为 `[Network request blocked]`

### Requirement: 预处理 SHALL 集成到 skill_view 加载流程
skill_view 工具加载技能内容时 SHALL 自动执行预处理。

#### Scenario: skill_view 触发预处理
- **WHEN** 调用 skill_view 加载技能时
- **THEN** 先执行预处理（变量替换 + shell 展开），再返回内容

#### Scenario: 预处理失败不影响加载
- **WHEN** 预处理过程中发生错误（如命令失败）
- **THEN** 记录警告日志，返回原始内容（未替换的部分保留原样）
