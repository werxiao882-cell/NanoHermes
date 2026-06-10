## 1. 显式工具加载语法（select:<name>）

- [x] 1.1 在 ToolSearch.search() 中新增 _parse_select_query() 方法，解析 `select:` 前缀和逗号分隔的工具名
- [x] 1.2 修改 ToolSearch.search() 逻辑：优先检测 select 语法，匹配则精确加载，否则回退 BM25/Regex
- [x] 1.3 添加工具选择数量限制（最多 10 个），超出时截断并忽略多余工具名
- [x] 1.4 编写 test_select_syntax 测试用例：单选、多选、不存在工具、空选择、超限截断
- [x] 1.5 编写 test_select_fallback 测试用例：验证非 select 查询仍走 BM25/Regex

## 2. 技能触发规则（TRIGGER/SKIP）

- [x] 2.1 修改 Skill dataclass，新增 trigger: list[str] 和 skip: list[str] 字段（默认空列表）
- [x] 2.2 修改 SkillLoader.load() 解析 SKILL.md frontmatter 中的 trigger 和 skip 字段
- [x] 2.3 修改 SkillManager.build_skill_prompt() 输出 TRIGGER/SKIP 内联格式
- [x] 2.4 编写 test_skill_trigger_rules 测试用例：有规则技能、无规则技能、trigger/skip 格式
- [x] 2.5 为现有 SKILL.md 文件添加 trigger/skip 示例（至少 2 个技能）

## 3. 系统提示词段落化重组

- [x] 3.1 修改 PromptAssembler.build_system_prompt_parts() 重组段落顺序和结构
- [x] 3.2 新增 _build_identity_section() 方法：加载 SOUL.md 作为 Identity 段落
- [x] 3.3 新增 _build_tool_usage_section() 方法：包含 Always-Loaded、Deferred、Guidelines 三个子段落
- [x] 3.4 新增 _build_skills_section() 方法：使用 TRIGGER/SKIP 内联格式
- [x] 3.5 新增 _build_operational_guidance_section() 方法：模型操作指导
- [x] 3.6 修改 _assemble_text() 确保段落间用双换行分隔
- [x] 3.7 编写 test_prompt_paragraphs 测试用例：完整段落结构、段落顺序、分隔符

## 4. 工具分组注入系统提示

- [x] 4.1 修改 _build_tool_usage_section() 使用 ToolRegistry.get_tool_categories_with_info() 获取分组
- [x] 4.2 实现 deferred tools 按 toolset 分组显示：`### <toolset>: <tool1>, <tool2>`
- [x] 4.3 在 Deferred Tools 标题添加加载提示："(use search_tools to discover)"
- [x] 4.4 编写 test_tool_grouping 测试用例：分组格式、单工具 toolset、多工具 toolset

## 5. 错误提示优化

- [x] 5.1 修改 dispatcher.py 检测工具是否在当前工具集中
- [x] 5.2 未加载工具返回结构化错误：InputValidationError + 加载提示
- [x] 5.3 编写 test_unloaded_tool_error 测试用例：未加载工具调用返回明确错误

## 6. 文档更新

- [ ] 6.1 更新 src/conversation/ARCHITECTURE.md 合并 prompt assembly 文档
- [ ] 6.2 更新 README.md 模块说明
- [ ] 6.3 更新 AGENTS.md 工具系统说明

## 7. 测试验证

- [ ] 7.1 运行 test_core_e2e.py 验证端到端功能
- [x] 7.2 运行 pytest tests/tools/ tests/skills/ tests/conversation/ 验证单元测试
- [x] 7.3 修复测试失败项（如有）
