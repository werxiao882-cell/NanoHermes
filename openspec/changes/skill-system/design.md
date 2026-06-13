## 上下文

业界成熟的自进化 AI Agent 系统的技能系统包含多个组件：

### Phase 1（已完成）

- `agent/skill_bundles.py` (~410 LOC): 技能捆绑
- `agent/curator.py` (~1780 LOC): 后台技能维护
- `tools/skill_usage.py`: 使用追踪
- SKILL.md 标准格式

### Phase 2（新增）

- `agent/skill_utils.py`: 轻量元数据工具（frontmatter 解析、平台匹配、禁用解析、条件提取）
- `agent/skill_preprocessing.py`: SKILL.md 预处理（模板变量替换、内联 shell 展开）
- `agent/skill_commands.py`: 斜杠命令桥接（扫描技能目录构建 /skill-name 命令）
- `agent/prompt_builder.py`: 系统提示组装（build_skills_system_prompt 构建分类索引，两层缓存）
- `tools/skills_guard.py`: 安全扫描器（正则静态分析，信任级别感知）
- `tools/skill_provenance.py`: 来源追踪（ContextVar 区分写入来源）
- `tools/skills_sync.py`: 内置技能同步（manifest seeding）
- `tools/skills_ast_audit.py`: AST 深度审计（检测动态 import/属性访问）

核心设计决策包括：
- SKILL.md frontmatter 标准（description≤60 字符）
- 技能捆绑 YAML 文件
- 使用追踪 sidecar JSON 文件
- Curator 空闲触发，后台审查
- 技能生命周期状态转换
- Pinned 技能豁免
- 变更前 tar.gz 备份
- **渐进式披露三层架构**（Tier 1/2/3）
- **来源保护**（bundled/hub/manual 不可被 Curator 触碰）
- **条件激活**（requires_tools/fallback_for_toolsets）
- **平台过滤**（platforms 字段按 OS 过滤）

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

### 3. 渐进式披露架构（Phase 2）

```python
class SkillProgressiveDisclosure:
    """三层加载策略，减少 system prompt token 消耗。"""
    
    # Tier 1: 系统提示索引（始终存在）
    def build_system_prompt_index(self) -> str:
        """构建分类索引：name + 一行描述。
        两层缓存：内存 LRU + 磁盘快照 (.skills_prompt_snapshot.json)
        """
        ...
    
    # Tier 2: 工具发现（按需加载）
    def skills_list(self, filter: str = "") -> list[dict]:
        """返回元数据（name, description, category），token 高效。"""
        ...
    
    def skill_view(self, name: str) -> dict:
        """返回完整内容 + 关联文件 + 环境要求。
        每次调用触发 usage tracking (bump_view + bump_use)
        """
        ...
    
    # Tier 3: 条件激活（动态显示）
    def _skill_should_show(self, skill: Skill, active_tools: set) -> bool:
        """评估 frontmatter 条件：
        - requires_toolsets: 需要指定工具集可用
        - requires_tools: 需要指定工具可用
        - fallback_for_toolsets: 指定工具集不可用时显示
        - fallback_for_tools: 指定工具不可用时显示
        """
        ...
```

### 4. 安全体系（Phase 2）

```python
class SkillGuard:
    """正则静态分析，检测外部来源技能的安全风险。"""
    
    PATTERNS = [
        (r"curl.*\$\{.*API_KEY.*\}", "exfiltration", "critical"),
        (r"wget.*--post-file", "exfiltration", "critical"),
        (r"eval\s*\(", "injection", "high"),
        (r"exec\s*\(", "injection", "high"),
        (r"rm\s+-rf\s+/", "destructive", "critical"),
        (r"mkfs\.", "destructive", "critical"),
        (r"crontab\s+-", "persistence", "high"),
        (r"systemctl\s+enable", "persistence", "medium"),
    ]
    
    def scan(self, skill_dir: Path) -> list[ScanResult]:
        """扫描技能目录中的所有文件。
        信任级别：builtin（跳过）> trusted（警告）> community（拒绝）
        """
        ...

from contextvars import ContextVar

write_origin: ContextVar[str] = ContextVar("write_origin", default="user")

class SkillProvenance:
    """区分技能来源，Curator 只管理 agent-created。"""
    
    SOURCES = ["bundled", "hub-installed", "agent-created", "manual"]
    
    def mark_agent_created(self, skill_name: str) -> None: ...
    def is_curator_eligible(self, skill_name: str) -> bool: ...
    def get_provenance(self, skill_name: str) -> str: ...

class SkillAstAuditor:
    """AST 深度审计，检测动态 import/属性访问。可选诊断，手动触发。"""
    
    def audit(self, skill_dir: Path) -> AuditReport: ...
```

### 5. 技能预处理（Phase 2）

```python
class SkillPreprocessor:
    """SKILL.md 加载时执行模板替换和 shell 展开。"""
    
    def preprocess(self, content: str, context: dict) -> str:
        """执行预处理：
        1. 模板变量替换：${HERMES_SKILL_DIR} -> 技能目录路径
        2. 内联 shell 展开：`!`command`` -> 命令输出
        """
        content = self._substitute_variables(content, context)
        content = self._expand_shell_commands(content)
        return content
    
    def _substitute_variables(self, content: str, context: dict) -> str:
        """替换 ${VAR_NAME} 格式的变量。"""
        ...
    
    def _expand_shell_commands(self, content: str) -> str:
        """展开 `!`command`` 为命令输出。
        安全限制：超时 5s，禁止危险命令。
        """
        ...
```

## 风险 / 权衡

| 风险 | 缓解措施 |
|------|---------|
| Curator 可能归档重要技能 | pinned 技能豁免，用户可恢复归档 |
| 技能使用追踪增加 I/O | 异步写入，批量更新 |
| SKILL.md 格式不一致 | 严格验证 frontmatter，警告但不拒绝 |
| 外部技能包含恶意代码 | SkillGuard 安全扫描 + 信任级别策略 |
| 渐进式披露增加复杂度 | 两层缓存（LRU + 磁盘快照）减少开销 |
| Shell 展开可能执行危险命令 | 超时限制 + 危险命令黑名单 |

