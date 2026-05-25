## 1. 项目设置

- [ ] 1.1 创建 `src/skills/` 目录结构
- [ ] 1.2 定义技能相关类型和接口
- [ ] 1.3 配置 vitest 测试框架

## 2. SkillLoader 实现

- [ ] 2.1 实现 SkillLoader 类
- [ ] 2.2 实现 parseFrontmatter 函数
- [ ] 2.3 实现 slugify 函数
- [ ] 2.4 实现 description 长度验证
- [ ] 2.5 编写 SkillLoader 的单元测试
  - [ ] 2.5.1 测试解析有效 SKILL.md
  - [ ] 2.5.2 测试 description 超过 60 字符
  - [ ] 2.5.3 测试缺少 frontmatter
  - [ ] 2.5.4 测试 slugify 特殊字符

## 3. 技能捆绑实现

- [ ] 3.1 实现 SkillBundleLoader 类
- [ ] 3.2 实现 YAML 捆绑文件解析
- [ ] 3.3 实现捆绑优先于技能的逻辑
- [ ] 3.4 编写技能捆绑的单元测试
  - [ ] 3.4.1 测试加载捆绑
  - [ ] 3.4.2 测试捆绑优先于技能

## 4. 技能使用追踪实现

- [ ] 4.1 实现 SkillUsageTracker 类
- [ ] 4.2 实现 sidecar JSON 文件读写
- [ ] 4.3 实现 use_count、view_count、patch_count 追踪
- [ ] 4.4 编写使用追踪的单元测试
  - [ ] 4.4.1 测试记录技能调用
  - [ ] 4.4.2 测试记录技能查看
  - [ ] 4.4.3 测试记录技能补丁

## 5. Curator 实现

- [ ] 5.1 实现 Curator 类
- [ ] 5.2 实现 maybeRun 方法（空闲触发）
- [ ] 5.3 实现 autoTransitions 方法
- [ ] 5.4 实现 archiveSkill 和 markStale 方法
- [ ] 5.5 实现 pinned 技能豁免
- [ ] 5.6 实现 tar.gz 备份
- [ ] 5.7 实现 spawnReviewAgent 方法
- [ ] 5.8 编写 Curator 的单元测试
  - [ ] 5.8.1 测试空闲时触发
  - [ ] 5.8.2 测试未空闲不触发
  - [ ] 5.8.3 测试间隔未到不触发
  - [ ] 5.8.4 测试转换为 stale
  - [ ] 5.8.5 测试转换为 archived
  - [ ] 5.8.6 测试 pinned 技能不转换
  - [ ] 5.8.7 测试创建备份

## 6. 技能生命周期测试

- [ ] 6.1 编写技能生命周期状态转换的单元测试
  - [ ] 6.1.1 测试 active → stale
  - [ ] 6.1.2 测试 stale → archived
  - [ ] 6.1.3 测试恢复归档技能
