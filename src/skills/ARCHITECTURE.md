# Skill System Architecture

## Responsibility
技能系统，支持 SKILL.md 标准格式、技能加载、使用追踪、Curator 后台自进化。
使 Agent 能够动态加载技能并自我进化。

## Components

```
┌──────────────────────────────────────────────────────────────┐
│                    SkillLoader                                │
│                                                              │
│  - Parse SKILL.md YAML frontmatter                           │
│  - Validate: name, description (≤60 chars), version, etc.   │
│  - Extract: body content, platforms, metadata                │
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
│  │  Skill Prompt Injection                                 │  │
│  │  - build_skill_prompt() → volatile layer               │  │
│  │  - Format: "## Available Skills\n- **name**: desc"     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Skill CRUD Operations                                  │  │
│  │  - create_skill(name, content, category)               │  │
│  │  - edit_skill(name, content)                           │  │
│  │  - patch_skill(name, old_string, new_string)           │  │
│  │  - delete_skill(name)                                  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    Curator                                    │
│                                                              │
│  - Background skill maintenance                              │
│  - Auto-transitions: active → stale → archived               │
│  - Thresholds: stale_after_days, archive_after_days          │
│  - Pinned skills exempt from auto-transitions                │
│  - Usage tracking: .usage.json sidecar file                  │
└──────────────────────────────────────────────────────────────┘

Skill Directory Structure:
~/.nanohermes/skills/
├── my-skill/
│   ├── SKILL.md
│   ├── references/
│   ├── templates/
│   ├── scripts/
│   └── assets/
└── category-name/
    └── another-skill/
        └── SKILL.md
```

## Data Flow
1. SkillManager 初始化时扫描技能目录加载所有 SKILL.md
2. 启用的技能通过 build_skill_prompt() 注入系统提示
3. Agent 调用技能时记录使用次数
4. Curator 定期审查技能，自动转换生命周期状态
5. 用户或 Agent 可以通过 skill_manage 工具创建/编辑/删除技能

## Design Decisions
- **Decision**: 技能目录结构支持分类和子目录
  - **Reason**: 便于组织大量技能
- **Decision**: Curator 使用 sidecar JSON 文件追踪使用
  - **Reason**: 轻量级，不依赖数据库
- **Decision**: Pinned 技能豁免自动转换
  - **Reason**: 保护重要技能不被自动归档

## Dependencies
- Internal: src/tools/impls/skills_tool.py (工具接口), src/config/ (配置模块)
- External: None
