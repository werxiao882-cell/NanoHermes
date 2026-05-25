## 上下文

业界成熟的自进化 AI Agent 系统的技能系统包含多个组件：
- `agent/skill_bundles.py` (~410 LOC): 技能捆绑
- `agent/curator.py` (~1780 LOC): 后台技能维护
- `tools/skill_usage.py`: 使用追踪
- SKILL.md 标准格式

核心设计决策包括：
- SKILL.md frontmatter 标准（description≤60 字符）
- 技能捆绑 YAML 文件
- 使用追踪 sidecar JSON 文件
- Curator 空闲触发，后台审查
- 技能生命周期状态转换
- Pinned 技能豁免
- 变更前 tar.gz 备份

## 技术方案

### 1. SKILL.md 解析器

```typescript
interface SkillFrontmatter {
  name: string;
  description: string;  // ≤60 字符
  version?: string;
  author?: string;
  license?: string;
  platforms?: string[];
  metadata?: {
    hermes?: {
      tags?: string[];
      category?: string;
      related_skills?: string[];
      config?: Record<string, any>;
    };
  };
}

export class SkillLoader {
  async load(skillDir: string): Promise<Skill> {
    const skillMdPath = join(skillDir, 'SKILL.md');
    const content = readFileSync(skillMdPath, 'utf-8');
    
    const { frontmatter, body } = parseFrontmatter(content);
    
    // 验证 description 长度
    if (frontmatter.description.length > 60) {
      logger.warn(`技能 ${frontmatter.name} 的 description 超过 60 字符 (${frontmatter.description.length})`);
    }
    
    return {
      dir: skillDir,
      frontmatter,
      body,
      slug: slugify(frontmatter.name)
    };
  }
}
```

### 2. Curator 后台维护

```typescript
export class Curator {
  private state: CuratorState;
  
  async maybeRun(): Promise<void> {
    if (this.isPaused()) return;
    if (!this.isIdle()) return;
    if (!this.isIntervalElapsed()) return;
    
    // 备份
    await this.backup();
    
    // 自动转换状态
    await this.autoTransitions();
    
    // 后台审查
    await this.spawnReviewAgent();
    
    // 更新状态
    this.updateState();
  }
  
  private async autoTransitions(): Promise<void> {
    const skills = this.getAgentCreatedSkills();
    
    for (const skill of skills) {
      if (skill.pinned) continue; // pinned 豁免
      
      const daysSinceActivity = daysSince(skill.lastActivityAt);
      
      if (daysSinceActivity >= this.archiveAfterDays) {
        await this.archiveSkill(skill);
      } else if (daysSinceActivity >= this.staleAfterDays) {
        await this.markStale(skill);
      }
    }
  }
}
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| Curator 可能归档重要技能 | pinned 技能豁免，用户可恢复归档 |
| 技能使用追踪增加 I/O | 异步写入，批量更新 |
| SKILL.md 格式不一致 | 严格验证 frontmatter，警告但不拒绝 |
