# src/skills/ ARCHITECTURE

## 模块概述

技能系统：解析 SKILL.md 标准格式，提供渐进式披露（三层加载 + 两层缓存）、安全扫描（正则 + AST）、来源追踪、预处理（模板变量替换）、Curator 后台自进化（active→stale→archived）。使 Agent 能动态发现并自我进化技能。

## 文件职责

| 文件 | 职责 |
|------|------|
| `__init__.py` | 模块入口，re-export 公共 API（SkillLoader, SkillManager, Curator 等） |
| `loader.py` | `SkillLoader` 解析 SKILL.md YAML frontmatter + `Skill` 数据类 |
| `manager.py` | `SkillManager` 编排器：加载、CRUD、分类推断、启用/禁用、使用追踪、提示注入 |
| `curator.py` | `Curator` 后台生命周期管理：active→stale→archived（仅管理 agent-created 技能） |
| `progressive_disclosure.py` | `SkillProgressiveDisclosure` 三层加载 + 两层缓存 + 条件激活 + 平台过滤 |
| `security.py` | 三合一安全：`SkillGuard`（正则扫描）、`SkillProvenance`（ContextVar 来源追踪）、`SkillAstAuditor`（AST 审计） |
| `preprocessing.py` | `substitute_template_vars()` 模板替换 + `expand_inline_shell()` shell 展开（当前未启用） |

## 核心数据流

```
启动时:
  skills_dir.rglob("SKILL.md")
       │
       ▼
  SkillLoader.load()  ──►  Skill(name, description, platforms, trigger, skip, body)
       │
       ▼
  SkillManager._skills: dict[name, SkillEntry]   ──(内存字典，重启后重置)

运行时 (Tier 1 → 系统提示注入):
  PromptAssembler
       │
       ▼
  SkillProgressiveDisclosure.build_system_prompt_index()
       │
       ├── L1 内存 LRU (OrderedDict, max 8)
       ├── L2 磁盘快照 (.skills_prompt_snapshot.json, mtime+size manifest)
       │
       ▼
  _scan_entries() → skill_matches_platform() → skill_should_show()
       │
       ▼
  分类索引文本 (name + description)  ──►  注入系统提示 volatile 层

按需加载 (Tier 2):
  skill_view 工具  ──►  SkillManager.get_skill_details()
       │
       ▼
  preprocess_skill_content()
       │
       └── substitute_template_vars()   # ${HERMES_SKILL_DIR} → /path/to/skill
           (expand_inline_shell 存在但 preprocess_skill_content 当前未调用)
       │
       ▼
  完整 SKILL.md 内容 + 支持文件列表  ──►  LLM 上下文

后台维护:
  Curator.maybe_run()  ──(idle ≥ 24h 且 interval ≥ 7天)──►
       │
       ▼
  _run_review(): 读取 .usage.json，检查 created_by=="agent"
       │
       ├── active  ──(30天无活动)──► stale
       └── stale   ──(90天无活动)──► archived
```

## 关键设计决策

**SKILL.md 作为唯一真实来源**：元数据（YAML frontmatter）与正文（Markdown）共存于同一文件，避免元数据与内容脱节。`SkillLoader` 优先 `yaml.safe_load`，无 yaml 库时回退简单 key:value 解析——优雅降级，减少硬性依赖。

**三层加载而非一次性注入**：完整 SKILL.md 约 36k token，全部注入系统提示会耗尽上下文。Tier 1 只注入 `name + description`（~200 token），Tier 2/3 按需加载——节省 ~80% token。

**两层缓存（内存 + 磁盘）**：内存 LRU 纳秒级命中但进程内失效；磁盘快照跨进程持久但需 manifest 验证。两者互补，冷启动时复用上次解析结果，避免重复 YAML 解析。

**正则作为主安全门，AST 作为补充诊断**：技能内容是 markdown/shell/YAML 混合格式，AST 无法解析；正则快速、语言无关，适合作为安装时的安全门。AST 审计仅用于 Python 文件的深度诊断，手动触发，不影响安装流程。

**信任基于来源而非内容**：同一 `curl | sh` 模式，builtin 技能允许执行，community 技能直接阻断。`SkillProvenance` 用 `ContextVar` 追踪写入来源（线程安全 + async 安全，无需锁），`Curator` 只管理 `created_by=="agent"` 的技能——bundled/manual 来源受保护。

**原子写入（tempfile + os.replace）**：同目录临时文件确保同一文件系统，`os.replace()` 是底层原子操作，崩溃时临时文件被清理、原文件保持完整。比 `shutil.move()` 可靠（后者可能退化为 copy+delete）。

**双层路径遍历防护**：L1 `_validate_file_path()` 快速拒绝 `".." in parts` 和 `parts[0] not in ALLOWED_SUBDIRS`（O(1)）；L2 `_resolve_skill_target()` 用 `resolve() + relative_to()` 验证绝对路径在技能目录内，防御符号链接攻击。

**预处理 never-raises 设计**：shell 展开的错误（超时、命令不存在、危险命令）都转为内联标记文本（如 `[Dangerous command blocked]`），不中断技能加载。shell 展开当前在 `preprocess_skill_content()` 中未调用，遵循最小权限原则。

**Curator 来源保护**：`created_by != "agent"` 的技能跳过审查，`pinned=True` 的技能豁免自动转换——保护用户手动创建或标记为重要的技能不被意外归档。

## 对外接口

### 公共类
- `Skill` — 技能元数据 dataclass（name, description, version, platforms, trigger, skip, body, path）
- `SkillEntry` — 技能运行时条目 dataclass（skill, enabled, use_count, last_used_at），manager 内部使用
- `SkillUsage` — Curator 使用追踪 dataclass（use_count, view_count, patch_count, last_activity_at, state, pinned）
- `SkillLoader` — `.load(path) → Skill`
- `SkillManager` — `.get_skill()`, `.list_skills()`, `.get_enabled_skills()`, `.list_skills_with_query()`, `.get_skills_by_category()`, `.get_skill_details()`, `.enable_skill()`, `.disable_skill()`, `.record_use()`, `.build_skill_prompt()`, `.create_skill()`, `.edit_skill()`, `.patch_skill()`, `.delete_skill()`, `.write_file()`, `.remove_file()`
- `Curator` — `.maybe_run() → bool`, `.record_use(name)`
- `SkillProgressiveDisclosure` — `.build_system_prompt_index(tools, toolsets, disabled) → str`, `.clear_cache()`
- `SkillGuard` — `.scan(skill_dir, source) → ScanResult`, `.should_allow_install(result) → (bool|None, str)`
- `SkillProvenance` — `.mark_agent_created(name)`, `.is_curator_eligible(name) → bool`, `.get_provenance(name) → str`
- `SkillAstAuditor` — `.audit(skill_dir) → list[AstFinding]`

### 公共函数（__all__ 导出）
- `skill_matches_platform(platforms) → bool`
- `skill_should_show(conditions, tools, toolsets) → bool`
- `extract_skill_conditions(frontmatter) → dict`
- `preprocess_skill_content(content, skill_dir, session_id) → str`
- `substitute_template_vars(content, skill_dir, session_id) → str`
- `expand_inline_shell(content, skill_dir, timeout) → str`
- `set_write_origin(origin) / reset_write_origin(token) / is_background_review() → bool`

### 模块级函数（未导出）
- `format_ast_report(findings, skill_name) → str` — 格式化 AST 审计报告
- `slugify(text) → str` — 文本转 slug（loader 内部使用）

## 依赖关系

- **内部依赖**：`src/tools/impls/skills_tool.py`（工具接口调用 SkillManager）、`src/conversation/`（提示组装调用 SkillProgressiveDisclosure）
- **外部依赖**：`yaml`（可选，无则回退简单解析）、`pathlib`、`json`、`ast`、`contextvars`、`subprocess`（标准库）
