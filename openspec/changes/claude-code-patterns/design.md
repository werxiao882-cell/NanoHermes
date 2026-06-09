## Context

NanoHermes 当前使用 BM25/Regex 双引擎工具搜索机制，模型通过 `search_tools` 工具按需发现延迟加载的工具。技能系统通过 SKILL.md 文件定义，注入到系统提示的 stable 层。

现有架构：
- 6 个核心工具始终加载（read_file, write_file, search_files, patch, terminal, search_tools）
- 11 个延迟工具通过 search_tools 发现
- 技能通过 SkillManager 加载，build_skill_prompt() 生成 markdown 列表

Claude Code 的实践表明：
1. 显式加载语法（`select:<name>`）比模糊搜索更精确
2. 技能触发规则（TRIGGER/SKIP）可减少误触发
3. 段落化系统提示词提高模型理解效率

## Goals / Non-Goals

**Goals:**
- ToolSearch 支持 `select:<name>[,<name>...]` 语法，精确加载指定工具
- 技能 SKILL.md 新增 trigger/skip 字段定义触发规则
- 系统提示词按 Claude Code 风格重组为明确段落
- 系统提示中按 toolset 分组展示延迟工具
- 未加载工具调用返回明确错误提示

**Non-Goals:**
- 不改变现有 BM25/Regex 搜索功能（保持向后兼容）
- 不改变工具注册机制（register_tool 保持不变）
- 不改变 ConversationLoop 动态工具发现流程
- 不引入新的外部依赖

## Decisions

### 1. select 语法解析策略

**Decision**: 在 `ToolSearch.search()` 中优先检测 `select:` 前缀，若匹配则直接精确加载，否则回退到 BM25/Regex

**Rationale**:
- `select:terminal,read_file` → 直接返回这两个工具的 schema
- 逗号分隔支持批量加载
- 保持向后兼容：非 select 查询走原有 BM25/Regex 流程

**Alternatives considered**:
- 新增独立 `load_tools()` 函数 → 拒绝，增加 API 复杂度
- 使用不同 mode 参数 → 拒绝，select 是查询内容的一部分，非模式切换

### 2. 技能触发规则存储格式

**Decision**: 在 SKILL.md YAML frontmatter 中新增 `trigger` 和 `skip` 字段，存储为字符串列表

**Rationale**:
```yaml
trigger:
  - "when the user wants to X"
  - "when asked to Y"
skip:
  - "when Z is already configured"
```
- 与现有 frontmatter 格式一致
- 字符串列表易于模型理解和匹配
- 支持多条件 OR 逻辑

### 3. 系统提示词段落结构

**Decision**: 按照 Claude Code 风格重组为明确段落，但**所有内容动态组装，禁止硬编码**

**Rationale**:
```
# Identity
{{ soul_md_content }}

# Tool Usage
## Always-Loaded Tools
{{ core_tools_list }}

## Deferred Tools (use search_tools to discover)
{{ deferred_tools_grouped_by_toolset }}

## Tool Selection Guidelines
{{ tool_guidelines }}

# Skills
## Active Skills
{{ skills_with_trigger_skip_rules }}

# Operational Guidance
当前模型：{{ model_name }}
{{ model_specific_guidance }}

# Memory Context
{{ memory_context }}

# User Profile
{{ user_profile }}

# Current Time
{{ timestamp }}
```

**动态组装策略**:
- `{{ core_tools_list }}`: 从 `ToolRegistry.get_tool_schemas(exclude_deferred=True)` 动态获取
- `{{ deferred_tools_grouped_by_toolset }}`: 从 `ToolRegistry.get_tool_categories_with_info()` 过滤 `defer_loading=True` 动态分组
- `{{ skills_with_trigger_skip_rules }}`: 从 `SkillManager.get_enabled_skills()` 动态获取，格式化 trigger/skip
- `{{ tool_guidelines }}`: 通用指导文本（可配置），不绑定具体工具名
- `{{ model_specific_guidance }}`: 根据 `model_name` 动态匹配（Gemini/OpenAI/Anthropic）
- `{{ memory_context }}`, `{{ user_profile }}`, `{{ timestamp }}`: 每轮动态注入

**禁止硬编码的工具名列表**: 所有工具名、分组、描述必须从注册表实时读取

### 4. 未加载工具错误提示

**Decision**: 在 `dispatcher.py` 中检测工具是否存在于当前工具集，若不存在则返回结构化错误

**Rationale**:
```json
{
  "error": "InputValidationError",
  "message": "工具 '{{tool_name}}' 未加载。使用 search_tools 查询 'select:{{tool_name}}' 加载后再调用。",
  "hint": "search_tools(query='select:{{tool_name}}')"
}
```

### 5. 禁止硬编码原则

**Decision**: 系统提示词组装的所有内容必须动态获取，禁止硬编码工具名、技能名、分组等

**Rationale**:
- 工具注册表是单一数据源，提示词组装器不应维护自己的工具列表
- 新增/删除工具时，提示词自动反映变化，无需修改 assembler 代码
- 技能触发规则存储在 SKILL.md 中，动态读取而非硬编码在提示模板中
- 模型操作指导根据 model_name 动态匹配，不硬编码特定模型的指导文本

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| select 语法与 BM25 查询冲突 | 优先检测 `select:` 前缀，明确区分 |
| 技能触发规则增加提示词长度 | 仅注入 active skills，精简描述 |
| 段落结构变更影响缓存命中率 | stable 层内容变化时重建缓存 |
| 向后兼容性 | BM25/Regex 搜索保持不变，select 为新增 |

## Migration Plan

1. 部署 `search_tool.py` 新增 select 语法支持
2. 更新现有 SKILL.md 文件添加 trigger/skip 字段
3. 更新 `assembler.py` 重组系统提示词段落
4. 更新 `dispatcher.py` 优化错误提示
5. 运行测试验证兼容性

**Rollback**: 若出现问题，回退到原有 BM25/Regex 搜索和简单技能注入

## Open Questions

- 是否需要为 select 语法设置加载数量限制？（建议：最多 10 个）
- 技能触发规则是否支持正则表达式匹配？（建议：初期用字符串包含，后续可扩展）
