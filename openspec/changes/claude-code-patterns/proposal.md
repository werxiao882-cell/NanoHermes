## Why

NanoHermes 当前的工具发现和技能注入机制存在以下问题：

1. **工具发现不够精确**：BM25/Regex 搜索返回最多 5 个结果，但用户可能需要精确加载特定工具，而非模糊匹配
2. **技能注入缺乏触发规则**：技能描述冗长，模型可能在不相关场景下误触发，或错过应该触发的场景
3. **系统提示词结构不够清晰**：三层架构（stable/context/volatile）虽然合理，但段落组织缺乏 Claude Code 那样的明确分段和优先级标记
4. **工具分组信息未充分利用**：工具按 toolset 分组，但系统提示中未体现这种分组结构

参考 Claude Code 的成功实践，引入显式加载语法、技能触发规则和段落化系统提示，可显著提升工具调用准确率和技能使用效率。

## What Changes

- **显式工具加载语法**：`ToolSearch` 支持 `select:<name>[,<name>...]` 语法，精确加载指定工具 schema
- **工具分组提示**：系统提示中按 toolset 分组展示延迟工具，标明加载方式
- **技能触发规则**：为每个技能定义 TRIGGER/SKIP 规则，明确何时应该/不应该使用技能
- **系统提示词段落化**：按照 Claude Code 风格重组提示词结构，分为 Identity、Tool Usage、Skills、Operational Guidance 等明确段落
- **错误提示优化**：直接调用未加载工具时，返回明确的 InputValidationError 并提示加载方式

## Capabilities

### New Capabilities
- `explicit-tool-loading`: 支持 `select:<name>` 语法精确加载工具 schema
- `skill-trigger-rules`: 技能 TRIGGER/SKIP 规则定义和注入机制
- `prompt-assembly-paragraphs`: 段落化系统提示词组装（按 Claude Code 风格）
- `tool-grouping-in-prompt`: 系统提示中按 toolset 分组展示工具

### Modified Capabilities
- `tool-search-engine`: 扩展 ToolSearch 支持 select 语法，保持 BM25/Regex 兼容
- `skill-system`: 技能 SKILL.md 新增 trigger/skip 字段，更新注入逻辑

## Impact

**Affected Code:**
- `src/tools/search_tool.py`: 新增 select 语法解析和精确加载
- `src/tools/dispatcher.py`: 优化未加载工具的错误提示
- `src/conversation/assembler.py`: 重组系统提示词段落结构
- `src/skills/loader.py`: Skill 数据类新增 trigger/skip 字段
- `src/skills/manager.py`: 更新技能提示构建逻辑

**Breaking Changes:**
- 无破坏性变更，select 语法为新增功能，BM25/Regex 搜索保持兼容

**Dependencies:**
- 无新增外部依赖
