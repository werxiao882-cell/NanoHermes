## ADDED Requirements

### Requirement: ToolEntry supports defer_loading field

The ToolEntry dataclass SHALL include a `defer_loading` boolean field, defaulting to `False`. When `True`, the tool SHALL NOT be included in the initial tool schemas passed to the LLM at startup.

#### Scenario: Default defer_loading is False
- **WHEN** a tool is registered without specifying `defer_loading`
- **THEN** the tool's `defer_loading` attribute SHALL be `False`

#### Scenario: Explicit defer_loading is True
- **WHEN** a tool is registered with `defer_loading=True`
- **THEN** the tool's `defer_loading` attribute SHALL be `True`

### Requirement: ToolRegistry filters deferred tools

The ToolRegistry SHALL provide methods to separate deferred and non-deferred tools. `get_tool_schemas(exclude_deferred=True)` SHALL return only schemas where `defer_loading=False`. `get_deferred_tools()` SHALL return all ToolEntry objects where `defer_loading=True`.

#### Scenario: Get schemas excluding deferred tools
- **WHEN** `get_tool_schemas(exclude_deferred=True)` is called
- **THEN** only schemas with `defer_loading=False` are returned

#### Scenario: Get deferred tools list
- **WHEN** `get_deferred_tools()` is called
- **THEN** all ToolEntry objects with `defer_loading=True` are returned

### Requirement: register_tool accepts defer_loading parameter

The module-level `register_tool()` function SHALL accept a `defer_loading` parameter and pass it through to ToolEntry.

#### Scenario: Register tool with defer_loading
- **WHEN** `register_tool(name="github_pr", ..., defer_loading=True)` is called
- **THEN** the registered tool entry has `defer_loading=True`

### Requirement: Core I/O tools are always loaded

The following 5 tools SHALL have `defer_loading=False` (always visible to the model). These form the core I/O loop: read files, search, edit, write, and execute commands.

| Tool | Toolset | Rationale |
|------|---------|-----------|
| `read_file` | file | Used in virtually every conversation to understand codebases, configs, logs |
| `write_file` | file | Essential for producing any output: new files, configs, generated code |
| `search_files` | file | Fundamental for navigating codebases, replacing grep/find/ls |
| `patch` | file | Primary editing tool for targeted modifications to existing files |
| `terminal` | terminal | Required for builds, git, installs, running scripts, shell operations |

#### Scenario: Core tools appear in initial schemas
- **WHEN** `get_tool_schemas(exclude_deferred=True)` is called after all tools are registered
- **THEN** the result contains exactly `read_file`, `write_file`, `search_files`, `patch`, `terminal` schemas

### Requirement: Non-core tools are deferred

The following 11 tools SHALL have `defer_loading=True` (discovered on-demand via `search_tools`). These are domain-specific, conditional, or low-frequency tools.

| Tool | Toolset | Discovery Trigger |
|------|---------|-------------------|
| `execute_code` | code_execution | Multi-step processing with 3+ tool calls |
| `process` | terminal | Background process management needed |
| `todo` | todo | Complex task with 3+ steps |
| `memory` | memory | Saving/reading persistent information |
| `session_search` | session_search | Recalling past session work |
| `clarify` | clarify | Ambiguity requiring user input |
| `skill_view` | skills | Loading a specific skill's content |
| `skills_list` | skills | Discovering available skills |
| `skill_manage` | skills | Creating/updating skills |
| `delegate_task` | delegation | Parallel or reasoning-heavy subtasks |
| `cronjob` | cronjob | Scheduling recurring tasks |

#### Scenario: Deferred tools are excluded from initial schemas
- **WHEN** `get_tool_schemas(exclude_deferred=True)` is called
- **THEN** none of the 11 deferred tools appear in the result

#### Scenario: Deferred tools are retrievable via get_deferred_tools
- **WHEN** `get_deferred_tools()` is called
- **THEN** all 11 deferred tools are returned
