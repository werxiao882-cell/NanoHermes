## MODIFIED Requirements

### Requirement: Tool interface security metadata
Tool 接口 SHALL 新增安全元数据声明字段：`is_concurrency_safe(input) -> bool`、`is_read_only(input) -> bool`、`is_destructive(input) -> bool`、`check_permissions(input, context) -> PermissionResult`、`prepare_permission_matcher(input) -> PermissionMatcher`。所有字段有 fail-closed 默认值。

#### Scenario: 新工具默认非并发安全
- **WHEN** 使用 `build_tool()` 创建工具且未指定 `is_concurrency_safe`
- **THEN** 默认值 SHALL 为 `lambda input: False`（不并发安全）

#### Scenario: 新工具默认非只读
- **WHEN** 使用 `build_tool()` 创建工具且未指定 `is_read_only`
- **THEN** 默认值 SHALL 为 `lambda input: False`（非只读，需要权限检查）

#### Scenario: 权限检查默认允许
- **WHEN** 使用 `build_tool()` 创建工具且未指定 `check_permissions`
- **THEN** 默认值 SHALL 返回 `PermissionResult(behavior='allow')`（由外层权限系统控制）

### Requirement: Tool deferred loading metadata
Tool 接口 SHALL 新增 `should_defer: bool` 和 `always_load: bool` 字段，控制工具是否延迟加载。`should_defer=True` 的工具不出现在初始 LLM 上下文中，通过 search_tools 按需发现。

#### Scenario: 延迟加载工具不出现在初始上下文
- **WHEN** 工具的 `should_defer` 为 True
- **THEN** 该工具的 schema SHALL 不出现在初始 API 调用的 tools 参数中
