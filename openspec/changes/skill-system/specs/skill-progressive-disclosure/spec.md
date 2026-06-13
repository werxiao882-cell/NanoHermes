## ADDED Requirements

### Requirement: 系统 SHALL 实现渐进式披露架构
技能系统 SHALL 采用三层加载策略，减少 system prompt token 消耗：
- **Tier 1**：系统提示索引（始终存在），包含 name + 一行描述的分类索引
- **Tier 2**：工具发现（按需加载），通过 skills_list/skill_view 工具
- **Tier 3**：条件激活（动态显示），根据 requires_tools/fallback_for_toolsets 评估

#### Scenario: 生成系统提示索引
- **WHEN** 构建系统提示时
- **THEN** 只包含技能的 name 和 description（≤60 字符），不包含完整内容

#### Scenario: 按需加载完整内容
- **WHEN** 模型调用 skill_view 工具时
- **THEN** 返回完整的 SKILL.md 内容 + 关联文件列表

#### Scenario: 缓存系统提示索引
- **WHEN** 技能目录未变化时
- **THEN** 使用内存 LRU 缓存或磁盘快照，避免重复构建

### Requirement: 系统 SHALL 实现两层缓存
系统提示索引 SHALL 使用两层缓存策略：
1. **内存 LRU 缓存**：进程内 dict，key 为 (skills_dir, tools, toolsets, platform, disabled)
2. **磁盘快照**：.skills_prompt_snapshot.json，包含 mtime/size manifest 验证

#### Scenario: 内存缓存命中
- **WHEN** 相同参数调用 build_system_prompt_index 时
- **THEN** 直接返回缓存结果，不重新扫描

#### Scenario: 磁盘快照验证
- **WHEN** 进程重启后首次构建索引时
- **THEN** 检查 skills 目录的 mtime/size，若未变化则加载快照

#### Scenario: 缓存失效
- **WHEN** 技能目录发生变化（新增/删除/修改）时
- **THEN** 重新扫描并更新缓存

### Requirement: 系统 SHALL 支持条件激活声明
技能 SHALL 在 frontmatter 的 metadata.hermes 中声明条件激活规则：
- `requires_toolsets: list[str]`：需要指定工具集可用才显示
- `requires_tools: list[str]`：需要指定工具可用才显示
- `fallback_for_toolsets: list[str]`：指定工具集不可用时显示
- `fallback_for_tools: list[str]`：指定工具不可用时显示

#### Scenario: 声明 requires_toolsets
- **WHEN** 技能 frontmatter 包含 `requires_toolsets: ["terminal", "file"]`
- **THEN** 只有 terminal 和 file 工具集都可用时才显示该技能

#### Scenario: 声明 fallback_for_tools
- **WHEN** 技能 frontmatter 包含 `fallback_for_tools: ["web_search"]`
- **THEN** 只有 web_search 工具不可用时才显示该技能（作为替代方案）

### Requirement: 系统 SHALL 评估条件激活规则
系统 SHALL 在构建系统提示索引时评估每个技能的条件激活规则，决定是否显示。

#### Scenario: 所有 requires_toolsets 满足
- **WHEN** 技能声明 requires_toolsets: ["terminal"] 且 terminal 工具集可用
- **THEN** _skill_should_show() 返回 True

#### Scenario: 部分 requires_toolsets 不满足
- **WHEN** 技能声明 requires_toolsets: ["terminal", "mcp"] 但 mcp 工具集不可用
- **THEN** _skill_should_show() 返回 False

#### Scenario: requires_tools 检查具体工具
- **WHEN** 技能声明 requires_tools: ["execute_code"] 且 execute_code 工具可用
- **THEN** _skill_should_show() 返回 True

#### Scenario: fallback_for_toolsets 触发
- **WHEN** 技能声明 fallback_for_toolsets: ["mcp"] 且 mcp 工具集不可用
- **THEN** _skill_should_show() 返回 True（作为 MCP 的替代方案）

#### Scenario: 无条件声明
- **WHEN** 技能 frontmatter 未声明任何条件激活规则
- **THEN** _skill_should_show() 返回 True（始终显示）

### Requirement: 系统 SHALL 支持平台过滤
技能 SHALL 在 frontmatter 中声明 `platforms` 字段，系统根据当前操作系统过滤技能可用性。支持的平台：
- `linux`：Linux 系统
- `macos`：macOS 系统
- `windows`：Windows 系统
- `termux`：Termux/Android 环境

#### Scenario: 平台匹配
- **WHEN** 技能声明 platforms: ["linux", "macos"] 且当前系统为 Linux
- **THEN** skill_matches_platform() 返回 True

#### Scenario: 平台不匹配
- **WHEN** 技能声明 platforms: ["linux"] 且当前系统为 Windows
- **THEN** skill_matches_platform() 返回 False

#### Scenario: 未声明 platforms
- **WHEN** 技能 frontmatter 未声明 platforms 字段
- **THEN** skill_matches_platform() 返回 True（所有平台可用）

### Requirement: 系统 SHALL 检测 Termux/Android 环境
系统 SHALL 特殊处理 Termux/Android 环境，优先匹配 `termux` 平台。

#### Scenario: Termux 环境检测
- **WHEN** 当前环境为 Termux（ANDROID_ROOT 环境变量存在）
- **THEN** 优先匹配 platforms 中的 "termux"

#### Scenario: Termux 环境回退
- **WHEN** 当前环境为 Termux 但技能未声明 "termux" 平台
- **THEN** 回退匹配 "linux" 平台

### Requirement: 条件激活和平台过滤 SHALL 组合评估
条件激活评估 SHALL 与平台过滤组合，两者都满足时才显示技能。

#### Scenario: 条件满足但平台不匹配
- **WHEN** 技能 requires_toolsets 满足但 platforms: ["linux"] 且当前为 Windows
- **THEN** _skill_should_show() 返回 False

#### Scenario: 条件和平台都满足
- **WHEN** 技能 requires_toolsets 满足且 platforms 匹配当前系统
- **THEN** _skill_should_show() 返回 True

### Requirement: 平台过滤 SHALL 集成到技能列表
skills_list 工具和系统提示索引 SHALL 自动过滤平台不匹配的技能。

#### Scenario: skills_list 过滤平台
- **WHEN** 调用 skills_list 工具时
- **THEN** 只返回平台匹配的技能

#### Scenario: 系统提示索引过滤平台
- **WHEN** 构建系统提示索引时
- **THEN** 只包含平台匹配的技能
