## 1. 项目设置

- [x] 1.1 创建 `src/skills/` 目录结构
- [x] 1.2 定义技能相关类型和接口
- [x] 1.3 配置 vitest 测试框架

## 2. SkillLoader 实现

- [x] 2.1 实现 SkillLoader 类
- [x] 2.2 实现 parseFrontmatter 函数
- [x] 2.3 实现 slugify 函数
- [x] 2.4 实现 description 长度验证
- [x] 2.5 编写 SkillLoader 的单元测试
  - [x] 2.5.1 测试解析有效 SKILL.md
  - [x] 2.5.2 测试 description 超过 60 字符
  - [x] 2.5.3 测试缺少 frontmatter
  - [x] 2.5.4 测试 slugify 特殊字符

## 3. 技能捆绑实现

- [x] 3.1 实现 SkillBundleLoader 类
- [x] 3.2 实现 YAML 捆绑文件解析
- [x] 3.3 实现捆绑优先于技能的逻辑
- [x] 3.4 编写技能捆绑的单元测试
  - [x] 3.4.1 测试加载捆绑
  - [x] 3.4.2 测试捆绑优先于技能

## 4. 技能使用追踪实现

- [x] 4.1 实现 SkillUsageTracker 类
- [x] 4.2 实现 sidecar JSON 文件读写
- [x] 4.3 实现 use_count、view_count、patch_count 追踪
- [x] 4.4 编写使用追踪的单元测试
  - [x] 4.4.1 测试记录技能调用
  - [x] 4.4.2 测试记录技能查看
  - [x] 4.4.3 测试记录技能补丁

## 5. Curator 实现

- [x] 5.1 实现 Curator 类
- [x] 5.2 实现 maybeRun 方法（空闲触发）
- [x] 5.3 实现 autoTransitions 方法
- [x] 5.4 实现 archiveSkill 和 markStale 方法
- [x] 5.5 实现 pinned 技能豁免
- [x] 5.6 实现 tar.gz 备份
- [x] 5.7 实现 spawnReviewAgent 方法
- [x] 5.8 编写 Curator 的单元测试
  - [x] 5.8.1 测试空闲时触发
  - [x] 5.8.2 测试未空闲不触发
  - [x] 5.8.3 测试间隔未到不触发
  - [x] 5.8.4 测试转换为 stale
  - [x] 5.8.5 测试转换为 archived
  - [x] 5.8.6 测试 pinned 技能不转换
  - [x] 5.8.7 测试创建备份

## 6. 技能生命周期测试

- [x] 6.1 编写技能生命周期状态转换的单元测试
  - [x] 6.1.1 测试 active → stale
  - [x] 6.1.2 测试 stale → archived
  - [x] 6.1.3 测试恢复归档技能

## 7. 技能管理工具实现

- [x] 7.1 将技能管理核心逻辑迁移到 SkillManager 类
- [x] 7.2 实现 skill_manage 工具（create, edit, patch, delete, write_file, remove_file）
- [x] 7.3 实现技能名称验证（≤64 字符，小写字母/数字/连字符/点/下划线）
- [x] 7.4 实现 SKILL.md 前置元数据验证（name, description, --- 格式）
- [x] 7.5 实现内容大小限制（SKILL.md ≤100k 字符，支持文件 ≤1MiB）
- [x] 7.6 实现原子写入（临时文件 + os.replace）
- [x] 7.7 实现路径安全验证（防止路径遍历，限制子目录）
- [x] 7.8 实现 skill_view 工具（查看技能详情和支持文件）
- [x] 7.9 实现 skills_list 工具（列出技能，支持关键词过滤）
- [x] 7.10 重构 skills_tools.py 使其只负责工具注册和调用
- [x] 7.11 编写技能管理工具的单元测试

---

## Phase 2：高级能力增强

## 8. 渐进式披露架构（skill-progressive-disclosure）

- [x] 8.1 实现 SkillProgressiveDisclosure 类
- [x] 8.2 实现 build_system_prompt_index 方法（Tier 1：分类索引）
- [x] 8.3 实现两层缓存（内存 LRU + 磁盘快照 .skills_prompt_snapshot.json）
- [x] 8.4 实现 _skill_should_show 方法（条件激活 + 平台过滤组合评估）
- [x] 8.5 实现 skill_matches_platform 函数（linux/macos/windows/termux）
- [x] 8.6 重构 prompt_builder 使用渐进式披露
- [x] 8.7 编写单元测试
  - [x] 8.7.1 测试系统提示索引生成
  - [x] 8.7.2 测试缓存命中/失效
  - [x] 8.7.3 测试条件激活逻辑（requires_toolsets/fallback_for_tools）
  - [x] 8.7.4 测试平台匹配和 Termux 回退

## 9. 安全体系（skill-security）

- [x] 9.1 实现 SkillGuard 类（正则静态分析）
- [x] 9.2 定义安全检测正则模式（exfiltration/injection/destructive/persistence）
- [x] 9.3 实现 scan 方法（递归扫描技能目录所有文件）
- [x] 9.4 实现信任级别策略（builtin/trusted/community）
- [x] 9.5 实现 SkillProvenance 类（来源追踪）
- [x] 9.6 实现 write_origin ContextVar（区分 user/background_review）
- [x] 9.7 实现 mark_agent_created / is_curator_eligible 方法
- [x] 9.8 集成来源追踪到 Curator（只管理 agent-created 技能）
- [x] 9.9 实现 SkillAstAuditor 类（AST 深度审计）
- [x] 9.10 实现动态 import/属性访问检测
- [x] 9.11 集成 SkillGuard 到 skill_manage
- [x] 9.12 编写单元测试
  - [x] 9.12.1 测试检测注入攻击/数据泄露/破坏性命令
  - [x] 9.12.2 测试信任级别策略
  - [x] 9.12.3 测试标记 agent-created
  - [x] 9.12.4 测试 Curator 跳过 bundled/hub/manual
  - [x] 9.12.5 测试 AST 审计检测动态 import

## 10. 技能预处理（skill-preprocessing）

- [x] 10.1 实现 SkillPreprocessor 类
- [x] 10.2 实现 _substitute_variables 方法（${VAR_NAME} 替换）
- [x] 10.3 实现 _expand_shell_commands 方法（`!`command`` 展开）
- [x] 10.4 实现安全限制（超时 5s + 危险命令黑名单）
- [x] 10.5 集成到 skill_view 加载流程
- [x] 10.6 编写单元测试
  - [x] 10.6.1 测试变量替换
  - [x] 10.6.2 测试 shell 展开
  - [x] 10.6.3 测试超时和黑名单
