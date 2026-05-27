## 为什么

业界成熟的自进化 AI Agent 系统拥有完整的技能系统，包括 SKILL.md 标准格式、技能捆绑、使用追踪、Curator 后台自进化循环。NanoHermes 需要实现相同的技能系统，使 Agent 能够动态加载技能并自我进化。

## 变更内容

- 实现 SKILL.md 标准格式解析和验证
- 实现技能加载器和技能捆绑支持
- 实现技能使用追踪
- 实现 Curator 后台技能维护
- 实现技能生命周期状态管理
- 实现 SkillManager 编排器，管理技能加载、启用/禁用
- 将技能内容注入到系统提示的 volatile 层，使模型知道可用技能
- 实现 CLI 命令：/skills list, /skills enable, /skills disable, /skills info
- 实现技能管理工具（skill_manage），支持创建、编辑、补丁、删除、写入文件、删除文件
- 实现技能查看工具（skill_view），查看技能详情和支持文件
- 实现技能列表工具（skills_list），列出可用技能并支持关键词过滤

## 能力

### 新增能力

- `skill-loader`: SKILL.md 解析器，支持 YAML frontmatter（name、description≤60 字符、version、author、license、platforms、metadata）。技能正文遵循现代章节顺序。
- `skill-bundles`: 技能捆绑，YAML 文件将多个技能组合在一个斜杠命令下。捆绑优先于同名技能。
- `skill-usage-tracking`: 技能使用追踪，记录 use_count、view_count、patch_count、last_activity_at、state（active/stale/archived）、pinned。
- `curator`: Curator 后台维护，定期审查 Agent 创建的技能，自动转换生命周期状态。空闲时触发（min_idle_hours），间隔后运行（interval_hours）。
- `skill-lifecycle`: 技能生命周期状态：active → stale（stale_after_days 后）→ archived（archive_after_days 后）。pinned 技能豁免所有自动转换。
- `skill-manager`: SkillManager 编排器，管理技能加载、启用/禁用、按名称查找。将技能描述注入系统提示 volatile 层，使模型知道可用技能。
- `skill-prompt-injection`: 技能提示注入，将已启用技能的描述和摘要注入到系统提示的 volatile 层。模型可根据需要请求使用技能。
- `skill-slash-commands`: 技能斜杠命令，使用 /skills, /skills enable, /skills disable 格式管理技能。
- `skill-manage-tool`: 技能管理工具，支持 create（创建）、edit（编辑）、patch（补丁）、delete（删除）、write_file（写入支持文件）、remove_file（删除支持文件）。参考 Hermes Agent 实现，包含名称验证、前置元数据验证、内容大小限制、原子写入、路径安全等。
- `skill-view-tool`: 技能查看工具，查看技能详情、元数据和支持文件列表。
- `skills-list-tool`: 技能列表工具，列出所有可用技能，支持关键词过滤。

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/skills/` 目录
- 与 OpenCode 技能系统集成
- 无破坏性变更，从零开始构建
