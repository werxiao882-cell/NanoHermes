# Skill System Architecture

## Responsibility
技能系统，支持 SKILL.md 标准格式、渐进式披露、安全扫描、来源追踪、预处理、Curator 后台自进化。
使 Agent 能够动态加载技能并自我进化。

## 目录结构

```
src/skills/
├── __init__.py                # 模块入口，re-export 核心 API
├── loader.py                  # SkillLoader（SKILL.md 解析、frontmatter 提取）
├── manager.py                 # SkillManager（技能编排器，CRUD + 分类 + 提示注入）
├── curator.py                 # Curator（后台生命周期管理，active→stale→archived）
├── progressive_disclosure.py  # 渐进式披露（三层加载 + 两层缓存 + 条件激活 + 平台过滤）
├── security.py                # 安全体系（SkillGuard + SkillProvenance + SkillAstAuditor）
├── preprocessing.py           # 预处理（模板变量替换 + 内联 shell 展开）
└── review_task.py             # 技能审查后台任务（BackgroundTaskScheduler 注册）
```

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    SkillLoader                                │
│                                                              │
│  - Parse SKILL.md YAML frontmatter                           │
│  - Validate: name, version, platforms, metadata              │
│  - Extract: body content, trigger/skip rules                 │
│  - slugify(): convert names to URL-friendly slugs            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    SkillManager                               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Skill Registry                                         │  │
│  │  - Load skills from ~/.nanohermes/skills/              │  │
│  │  - Enable/disable skills                               │  │
│  │  - Record usage (use_count, view_count, patch_count)   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Skill CRUD Operations                                  │  │
│  │  - create_skill(name, content, category)               │  │
│  │  - edit_skill(name, content)                           │  │
│  │  - patch_skill(name, old_string, new_string)           │  │
│  │  - delete_skill(name)                                  │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Progressive  │ │   Security   │ │Preprocessing │
│  Disclosure  │ │    System    │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Curator                                    │
│                                                              │
│  - Background skill maintenance                              │
│  - Auto-transitions: active → stale → archived               │
│  - Only manages agent-created skills (provenance protection) │
│  - Pinned skills exempt from auto-transitions                │
│  - Usage tracking: .usage.json sidecar file                  │
└──────────────────────────────────────────────────────────────┘

Skill Directory Structure:
~/.nanohermes/skills/
├── my-skill/                    ← 扁平结构（无分类）
│   ├── SKILL.md                 ← 唯一必需文件：元数据 + 指导正文
│   ├── references/              ← 参考文档：API 规范、协议说明、最佳实践
│   ├── templates/               ← 模板文件：代码片段、提示模板、配置模板
│   ├── scripts/                 ← 辅助脚本：Python/Shell/Bash 自动化脚本
│   └── assets/                  ← 静态资源：JSON 配置、图片、数据文件
└── category-name/               ← 分类目录（可选，自动推断）
    └── another-skill/
        └── SKILL.md
```

### Skill Directory Design (目录结构设计)

技能采用**目录包**而非单文件设计，因为技能不只是"一段提示词"，而是一个**完整的知识包**。
SKILL.md 是入口（~36k token 上限），但复杂技能需要附带参考文档、模板、脚本等辅助资源。

#### 各目录职责

| 目录 | 职责 | 典型文件 | 加载时机 |
|------|------|----------|----------|
| `SKILL.md` | 技能元数据 + 指导正文（唯一必需文件） | — | Tier 1 索引 / Tier 2 全文 |
| `references/` | 参考文档，供 LLM 查阅的外部知识 | API 规范、协议说明、RFC 摘录 | `skill_view` 按需加载 |
| `templates/` | 可复用的代码/配置模板 | 代码片段、提示模板、YAML 模板 | `skill_view` 按需加载 |
| `scripts/` | 可执行的辅助脚本 | Python/Shell/Bash 脚本 | LLM 通过 terminal 调用 |
| `assets/` | 静态资源和数据文件 | JSON 配置、图片、数据集 | `skill_view` 按需加载 |

`get_skill_details()` 自动遍历白名单子目录收集支持文件，`skill_view` 加载时一并返回给 LLM。

#### 白名单约束（`ALLOWED_SUBDIRS`）

```python
ALLOWED_SUBDIRS = {"references", "templates", "scripts", "assets"}
```

固定子目录白名单同时实现三个目标：

1. **安全防护**：`_validate_file_path()` 检查 `parts[0] not in ALLOWED_SUBDIRS`，阻止 `write_file`/`patch` 写入 `SKILL.md` 或技能目录外的文件（如 `../../etc/passwd`）
2. **结构一致性**：所有技能结构相同，`rglob` 扫描结果可预测，`get_skill_details()` 无需额外配置即可发现所有资源
3. **语义清晰**：四个目录名直接表达资源用途，技能作者无需查阅文档即可知道文件应放在哪里

#### 扁平 vs 嵌套结构

技能支持两种目录组织方式，`SkillManager` 自动适配：

```
# 扁平结构（无分类）—— 适合技能数量少（<10）的场景
~/.nanohermes/skills/
├── git-workflow/SKILL.md
├── code-review/SKILL.md
└── deploy-check/SKILL.md

# 嵌套结构（有分类）—— 适合技能数量多、需要分组的场景
~/.nanohermes/skills/
├── devops/
│   ├── deploy-check/SKILL.md
│   └── monitoring/SKILL.md
├── coding/
│   ├── code-review/SKILL.md
│   └── refactoring/SKILL.md
└── writing/
    └── doc-writer/SKILL.md
```

**分类自动推断**：`get_skills_by_category()` 从路径推断分类，无需在 SKILL.md 中声明：

```python
parts = rel.parts
category = parts[0] if len(parts) >= 2 else "other"
# skills/git-workflow/SKILL.md       → parts=("git-workflow",)  → "other"
# skills/devops/deploy-check/SKILL.md → parts=("devops","deploy-check") → "devops"
```

**创建时指定**：`create_skill(name, content, category="devops")` 自动创建分类目录。

**删除时清理**：删除技能后检查分类目录是否为空，空则一并删除，保持目录整洁。

**渐进式披露中的分类索引**：Tier 1 索引按分类分组展示，多分类时显示 `## category` 标题：

```
# Skills

## devops
- **deploy-check**: 部署前检查清单
- **monitoring**: 监控配置指导

## coding
- **code-review**: 代码审查流程

Before replying, scan the skills above...
```

#### 为什么存储在 `~/.nanohermes/` 而非项目目录内

与项目的数据存储约定一致——会话（`sessions.db`）、记忆（`memory/`）、MCP 配置（`mcp_servers.json`）都在 `~/.nanohermes/` 下。
技能是**用户级资源**，跨项目共享，不随项目仓库变化。

#### 扫描排除规则

```python
_EXCLUDED_DIRS = frozenset({
    ".git", ".github", ".hub", ".archive", ".venv", "venv",
    "node_modules", "site-packages", "__pycache__", ...
})
```

扫描时跳过隐藏目录、缓存、虚拟环境等，避免误加载非技能文件。
`.archive` 是 Curator 归档技能的目标目录，排除后归档技能不再出现在索引中。

### Progressive Disclosure (progressive_disclosure.py)

三层加载策略，减少 system prompt token 消耗：

```
┌──────────────────────────────────────────────────────────────┐
│  Tier 1: System Prompt Index (always present)                │
│  - Compact index: name + one-line description                │
│  - Categorized by skill category                             │
│  - Two-layer cache: memory LRU + disk snapshot               │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Tier 2: Tool Discovery (on-demand)                          │
│  - skills_list: metadata only (token-efficient)              │
│  - skill_view: full content + linked files                   │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Tier 3: Conditional Activation                              │
│  - skill_should_show(): evaluate frontmatter conditions      │
│  - requires_toolsets / requires_tools: hide if unavailable   │
│  - fallback_for_toolsets / fallback_for_tools: show if       │
│    primary unavailable                                       │
│  - skill_matches_platform(): filter by OS (linux/macos/      │
│    windows/termux)                                           │
└──────────────────────────────────────────────────────────────┘

Two-Layer Cache:
1. Memory LRU: OrderedDict, max 8 entries
   Key: (skills_dir, tools, toolsets, disabled)
2. Disk Snapshot: .skills_prompt_snapshot.json
   Validation: mtime/size manifest
```

### Security System (security.py)

```
┌──────────────────────────────────────────────────────────────┐
│  SkillGuard (Regex Static Analysis)                          │
│                                                              │
│  Threat Pattern Categories:                                  │
│  - exfiltration: curl/wget with secrets, SSH/AWS key access  │
│  - injection: eval/exec, prompt injection, developer mode    │
│  - destructive: rm -rf /, mkfs, dd if=/dev/zero              │
│  - persistence: crontab, systemd, shell rc mods              │
│  - network: reverse shells, tunnels (ngrok/cloudflared)      │
│  - obfuscation: base64 pipes, echo-pipe-to-shell             │
│  - supply_chain: curl-pipe-to-shell, unpinned pip/npm        │
│                                                              │
│  Trust Levels:                                               │
│  - builtin: skip scanning                                    │
│  - trusted: warn only                                        │
│  - community: block on caution/dangerous                     │
│  - agent-created: ask on dangerous                           │
│                                                              │
│  should_allow_install(): trust matrix decision               │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  SkillProvenance (ContextVar Tracking)                       │
│                                                              │
│  Sources: bundled / hub-installed / agent-created / manual   │
│                                                              │
│  write_origin ContextVar:                                    │
│  - default: "foreground" (user-directed writes)              │
│  - "background_review" (Curator fork writes)                 │
│                                                              │
│  mark_agent_created(): tag skill as agent-created            │
│  is_curator_eligible(): only agent-created can be managed    │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  SkillAstAuditor (AST Deep Audit)                            │
│                                                              │
│  Opt-in diagnostic, not security gate                        │
│                                                              │
│  Detects:                                                    │
│  - dynamic_import: importlib.import_module()                 │
│  - dynamic_import_computed: __import__(non-literal)          │
│  - dynamic_getattr: getattr(obj, non-literal)                │
│  - dict_access: obj.__dict__[non-literal]                    │
│  - importlib_import: import importlib                        │
│                                                              │
│  format_ast_report(): human-readable findings                │
└──────────────────────────────────────────────────────────────┘
```

### Preprocessing (preprocessing.py)

```
┌──────────────────────────────────────────────────────────────┐
│  Template Variable Substitution                              │
│                                                              │
│  Supported variables:                                        │
│  - ${HERMES_SKILL_DIR} → skill directory absolute path       │
│  - ${HERMES_SESSION_ID} → current session ID                 │
│  - ${HERMES_HOME} → ~/.nanohermes path                       │
│                                                              │
│  Unresolved variables preserved for debugging                │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  Inline Shell Expansion                                      │
│                                                              │
│  Syntax: !`command` → command output                         │
│                                                              │
│  Security limits:                                            │
│  - Timeout: 5 seconds (configurable)                         │
│  - Dangerous commands blocked: rm -rf /, mkfs, curl, wget    │
│  - Output truncated: 4000 chars max                          │
│  - Never raises: errors become inline markers                │
│                                                              │
│  Default: disabled (opt-in via config)                       │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

1. SkillManager 初始化时扫描技能目录加载所有 SKILL.md
2. PromptAssembler 调用 SkillProgressiveDisclosure 构建系统提示索引（Tier 1）
3. 索引应用条件激活（skill_should_show）和平台过滤（skill_matches_platform）
4. Agent 调用 skill_view 时触发预处理（模板替换 + shell 展开）
5. Agent 调用技能时记录使用次数
6. Curator 定期审查技能，只管理 agent-created 来源（来源保护）
7. 用户或 Agent 可以通过 skill_manage 工具创建/编辑/删除技能
8. 创建技能时检查 is_background_review()，标记 agent-created 来源

## 技能包设计技巧

### 1. SKILL.md 单一真实来源（Single Source of Truth）

SKILL.md 是技能包的唯一权威定义，采用 YAML frontmatter + Markdown 正文的混合格式：

```
---
name: my-skill          # 必需：机器可读标识符
description: 简短描述    # 必需：≤1024 字符，注入系统提示
version: 1.0.0          # 可选：语义化版本
platforms: [linux, macos]  # 可选：平台过滤
trigger: when X; when Y    # 可选：触发规则
skip: when Z               # 可选：跳过规则
---
# 技能正文（Markdown 格式的详细指导）
```

**设计理由**：
- **元数据与内容共存**：frontmatter 提供结构化元数据（供程序解析），正文提供自然语言指导（供 LLM 理解），两者在同一文件中，避免元数据与内容脱节
- **YAML 优先 + 简单解析回退**：`SkillLoader` 优先使用 `yaml.safe_load` 解析（支持嵌套结构、列表），无 yaml 库时回退到简单 key:value 解析，实现**优雅降级**
- **BOM 字符容错**：`text.lstrip("\ufeff")` 处理 Windows 编辑器可能添加的 BOM 头，避免解析失败

### 2. 渐进式披露（Progressive Disclosure）

三层加载策略是技能系统最核心的 token 优化技巧：

```
Tier 1（系统提示索引）→ Tier 2（工具发现）→ Tier 3（条件激活）
    ~200 tokens            按需加载             动态过滤
```

**设计理由**：
- **Tier 1 紧凑索引**：只注入 `name + description`（一行一个技能），相比加载完整 SKILL.md 节省 ~80% token
- **Tier 2 按需加载**：`skills_list` 返回元数据，`skill_view` 返回完整内容 + 支持文件，LLM 只在需要时才加载详情
- **Tier 3 条件激活**：`skill_should_show()` 根据当前可用工具集动态显示/隐藏技能
  - `requires_tools`: 必需工具不可用时隐藏（技能无法工作）
  - `fallback_for_tools`: 主工具可用时隐藏（技能是后备方案）
- **平台过滤**：`skill_matches_platform()` 支持 Termux/Android 特殊处理——`sys.platform` 在不同 Python 版本可能返回 `"linux"` 或 `"android"`，通过 `ANDROID_ROOT` 环境变量检测 Termux 环境

### 3. 两层缓存（Two-Layer Cache）

```
┌─────────────────────────────────┐
│  L1: 内存 LRU (OrderedDict)     │  纳秒级命中，max 8 entries
│  Key: (dir, tools, toolsets,    │
│        disabled)                │
├─────────────────────────────────┤
│  L2: 磁盘快照 (.json)           │  毫秒级命中，跨进程持久
│  验证: mtime_ns + size manifest │
└─────────────────────────────────┘
```

**设计理由**：
- **L1 内存缓存**：`OrderedDict` 实现 LRU，`threading.Lock` 保证线程安全，缓存键使用 `frozenset` 确保可哈希
- **L2 磁盘快照**：`.skills_prompt_snapshot.json` 存储解析后的条目和 manifest，manifest 对比 `mtime_ns + size` 判断文件是否变化
- **冷路径优化**：`_build_index()` 先检查 L2 快照，manifest 匹配时直接复用缓存条目，避免重复解析 YAML

### 4. 纵深防御安全（Defense in Depth）

三层安全机制，各司其职：

| 层级 | 组件 | 检测方式 | 触发时机 |
|------|------|----------|----------|
| L1 | SkillGuard | 正则匹配 30+ 威胁模式 | 安装时 |
| L2 | SkillProvenance | ContextVar 追踪写入来源 | 创建时 |
| L3 | SkillAstAuditor | AST 遍历检测动态行为 | 手动触发 |

**信任矩阵**（`INSTALL_POLICY`）：

```
              safe      caution    dangerous
builtin       allow     allow      allow
trusted       allow     allow      block
community     allow     block      block
agent-created allow     allow      ask
```

**设计理由**：
- **正则而非 AST 作为主安全门**：正则快速、语言无关、适用于 markdown/shell/YAML 等混合格式；AST 仅用于 Python 文件的深度诊断
- **信任基于来源而非内容**：同一 `curl | sh` 模式，builtin 技能允许执行，community 技能直接阻断
- **ContextVar 追踪**：`_write_origin` 使用 `contextvars.ContextVar` 实现，线程安全 + async 安全，无需锁

### 5. 原子写入（Atomic Write）

所有文件写入使用 `_atomic_write_text()` 确保崩溃安全：

```python
fd, temp_path = tempfile.mkstemp(dir=file_path.parent, ...)  # 同目录临时文件
os.fdopen(fd, "w").write(content)                              # 写入临时文件
os.replace(temp_path, file_path)                               # 原子替换
```

**设计理由**：
- **同目录临时文件**：`os.replace()` 要求源和目标在同一文件系统，`mkstemp(dir=...)` 确保这一点
- **`os.replace()` 而非 `shutil.move()`**：前者是底层系统调用，保证原子性；后者可能退化为 copy+delete
- **崩溃安全**：写入中断时临时文件被清理，原文件保持完整

### 6. 双层路径遍历防护

```
L1: _validate_file_path()     → 白名单检查 + ".." 组件检测
L2: _resolve_skill_target()   → resolve() + relative_to() 验证
```

**设计理由**：
- **L1 快速拒绝**：检查 `".." in normalized.parts` 和 `parts[0] not in ALLOWED_SUBDIRS`，O(1) 复杂度拦截明显恶意输入
- **L2 深度验证**：`target.resolve()` 解析符号链接和 `..`，`relative_to(skill_dir.resolve())` 确保目标在技能目录内，防御符号链接攻击
- **为什么需要两层**：L1 防止常见攻击向量（如 `../../etc/passwd`），L2 防御更隐蔽的攻击（如符号链接指向外部目录）

### 7. Curator 生命周期管理

```
active ──(30天无活动)──▶ stale ──(90天无活动)──▶ archived
  ▲                        │
  └──(用户再次使用)─────────┘
```

**设计理由**：
- **来源保护**：`created_by != "agent"` 的技能跳过审查，bundled/manual/hub-installed 来源受保护
- **Pinned 豁免**：`pinned=True` 的技能跳过自动转换，保护重要技能不被归档
- **Sidecar 文件**：使用 `.usage.json`（隐藏文件）存储使用数据，与技能目录同级，不污染技能内容
- **幂等审查**：`maybe_run()` 检查 `min_idle_hours` 和 `interval_hours`，避免频繁运行

### 8. 预处理管线（Preprocessing Pipeline）

```
SKILL.md 原始内容
    │
    ▼
substitute_template_vars()    # ${HERMES_SKILL_DIR} → /path/to/skill
    │
    ▼
expand_inline_shell()         # !`git branch` → main    (默认禁用)
    │
    ▼
预处理后内容（注入 LLM 上下文）
```

**设计理由**：
- **模板变量白名单**：只支持 3 个预定义变量（`HERMES_SKILL_DIR`、`HERMES_SESSION_ID`、`HERMES_HOME`），未解析的变量保留原样便于调试
- **Shell 展开默认禁用**：`expand_inline_shell()` 存在但不在 `preprocess_skill_content()` 中调用，需要显式启用，遵循最小权限原则
- **危险命令阻断**：`_DANGEROUS_RE` 正则匹配 `rm -rf`、`curl`、`wget` 等，阻断后返回 `[Dangerous command blocked]` 标记而非抛出异常
- **Never-raises 设计**：所有错误（超时、命令不存在、异常）都转为内联标记文本，不中断技能加载流程

### 9. 名称验证与跨平台兼容

```python
VALID_NAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
```

**设计理由**：
- **全小写**：避免 Windows（大小写不敏感）和 Linux（大小写敏感）的行为差异
- **以字母/数字开头**：避免 `.hidden` 隐藏文件问题和 URL 编码问题
- **限制字符集**：仅允许 `[a-z0-9._-]`，确保文件系统安全且 URL 友好
- **64 字符上限**：某些文件系统对路径长度有限制，64 字符足够表达语义名称

### 10. 容错加载（Fault-Tolerant Loading）

```python
for skill_file in sorted(self.skills_dir.rglob("SKILL.md")):
    try:
        skill = self._loader.load(skill_file)
        self._skills[skill.name] = SkillEntry(skill=skill)
    except Exception as e:
        logger.warning(f"加载技能失败 {skill_file}: {e}")  # 单个失败不影响其他
```

**设计理由**：
- **单技能隔离**：一个技能加载失败（格式错误、文件损坏）不影响其他技能，系统仍可用
- **YAML 可选依赖**：`try: import yaml` 在模块顶部执行，无 yaml 库时 `_HAS_YAML = False`，回退到简单解析
- **sorted() 确定性**：`rglob` 结果排序确保加载顺序可预测，便于调试和测试

## Dependencies

- Internal: src/tools/impls/skills_tool.py (工具接口), src/conversation/assembler.py (提示集成), src/background/scheduler.py (后台任务调度)
- External: None

## review_task（技能审查后台任务）

通过 `BackgroundTaskScheduler` 注册，在对话结束后自动审查并创建/更新技能：
- 触发条件：对话轮数 >= 10 且距离上次审查 >= 30 分钟
- 使用 `fork_agent` 进行技能审查，支持工具调用循环（skill_manage）
- 审查最近 20 条消息，每条截断到 500 字符
- 通过 `_SKILL_REVIEW_PROMPT` 引导 Agent 识别可复用的工作流并创建技能
