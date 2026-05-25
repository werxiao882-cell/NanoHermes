## ADDED Requirements

### Requirement: 系统 SHALL 支持 SKILL.md 标准格式
技能 SHALL 在 SKILL.md 文件中定义，包含 YAML frontmatter：name、description（≤60 字符）、version、author、license、platforms、metadata。技能正文 SHALL 遵循现代章节顺序。

#### Scenario: 加载 SKILL.md
- **WHEN** 技能目录包含 SKILL.md
- **THEN** 系统解析 frontmatter 并加载技能内容

#### Scenario: 验证 description 长度
- **WHEN** 技能 description 超过 60 字符
- **THEN** 系统在加载时发出警告

### Requirement: 系统 SHALL 支持技能捆绑
技能捆绑 SHALL 是 YAML 文件，将多个技能组合在一个斜杠命令下。调用捆绑时加载所有引用技能的内容到单个用户消息中。捆绑 SHALL 优先于同名技能。

#### Scenario: 加载技能捆绑
- **WHEN** 用户调用捆绑命令
- **THEN** 捆绑中的所有技能一起加载

#### Scenario: 捆绑优先于技能
- **WHEN** 捆绑和技能同名
- **THEN** 加载捆绑而非技能

### Requirement: 系统 SHALL 追踪技能使用
系统 SHALL 维护使用追踪 sidecar 文件，记录每个技能的：use_count、view_count、patch_count、last_activity_at、state（active/stale/archived）、pinned。

#### Scenario: 记录技能使用
- **WHEN** 技能被调用
- **THEN** use_count 递增，last_activity_at 更新

### Requirement: Curator SHALL 运行后台技能维护
Curator SHALL 定期审查 Agent 创建的技能并自动转换生命周期状态。空闲时触发（min_idle_hours 无用户活动），间隔后运行（interval_hours）。

#### Scenario: 空闲时触发 Curator
- **WHEN** Agent 空闲 min_idle_hours 且 interval_hours 已过
- **THEN** Curator spawn 后台审查进程

#### Scenario: 仅审查 Agent 创建的技能
- **WHEN** Curator 运行时
- **THEN** 只审查 created_by="agent" 的技能

### Requirement: 技能 SHALL 有生命周期状态
技能 SHALL 经历状态转换：active → stale（stale_after_days 后）→ archived（archive_after_days 后）。pinned 技能 SHALL 豁免所有自动转换。归档可恢复；技能永不自动删除。

#### Scenario: 自动转换为 stale
- **WHEN** 技能在 stale_after_days 内无活动
- **THEN** 状态转换为 stale

#### Scenario: 归档 stale 技能
- **WHEN** stale 技能达到 archive_after_days
- **THEN** 移动到归档目录并标记为 archived

#### Scenario: pinned 技能豁免
- **WHEN** pinned 技能达到 archive_after_days
- **THEN** 保持 active，不被归档

### Requirement: Curator SHALL 在变更前备份
在进行任何更改之前，Curator SHALL 创建技能目录的 tar.gz 备份。备份 SHALL 可通过 rollback 命令恢复。

#### Scenario: Curator 运行前备份
- **WHEN** Curator 启动审查周期
- **THEN** 创建带时间戳的 tar.gz 备份
