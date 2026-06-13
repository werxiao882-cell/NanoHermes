## 为什么

业界成熟的自进化 AI Agent 系统拥有完整的技能系统，包括 SKILL.md 标准格式、技能捆绑、使用追踪、Curator 后台自进化循环。NanoHermes 需要实现相同的技能系统，使 Agent 能够动态加载技能并自我进化。

**Phase 2 增强**：参考 hermes-agent-ref 实现，补充渐进式披露架构、安全体系、技能预处理等高级能力。

## 变更内容

### Phase 1（已完成）

- [x] 实现 SKILL.md 标准格式解析和验证
- [x] 实现技能加载器和技能捆绑支持
- [x] 实现技能使用追踪
- [x] 实现 Curator 后台技能维护
- [x] 实现技能生命周期状态管理
- [x] 实现 SkillManager 编排器，管理技能加载、启用/禁用
- [x] 将技能内容注入到系统提示的 volatile 层，使模型知道可用技能
- [x] 实现 CLI 命令：/skills list, /skills enable, /skills disable, /skills info
- [x] 实现技能管理工具（skill_manage），支持创建、编辑、补丁、删除、写入文件、删除文件
- [x] 实现技能查看工具（skill_view），查看技能详情和支持文件
- [x] 实现技能列表工具（skills_list），列出可用技能并支持关键词过滤

### Phase 2（新增）

- 实现渐进式披露架构（Tier 1/2/3），减少 system prompt token 消耗
- 实现安全扫描器（skills_guard），正则检测注入/泄露/破坏性命令
- 实现来源追踪（skill_provenance），区分 bundled/hub/agent-created
- 实现条件激活（requires_tools / fallback_for_toolsets），按工具集动态显示
- 实现平台过滤（platforms 字段），按 OS 过滤技能可用性
- 实现技能预处理（skill_preprocessing），模板变量替换、内联 shell 展开
- 实现技能 AST 深度审计（skills_ast_audit），检测动态 import/属性访问

## 能力

### 新增能力

#### Phase 1（已完成）

- `skill-loader`: SKILL.md 解析器 + 技能捆绑 + 使用追踪 + Curator + 生命周期管理 + SkillManager 编排器 + 工具集成（skill_manage/skill_view/skills_list）

#### Phase 2（新增）

- `skill-progressive-disclosure`: 渐进式披露架构（三层加载 + 两层缓存 + 条件激活 + 平台过滤）
- `skill-security`: 安全体系（正则扫描 + 信任级别 + 来源追踪 + ContextVar + AST 深度审计）
- `skill-preprocessing`: 技能预处理（模板变量替换 + 内联 shell 展开 + 安全限制）

### 修改能力

<!-- 无现有能力需要修改 -->

## 影响

- 新增 `src/skills/` 目录（Phase 1 已完成）
- 与 OpenCode 技能系统集成
- Phase 2 新增安全扫描、来源追踪、条件激活等模块
- 无破坏性变更，渐进式增强
