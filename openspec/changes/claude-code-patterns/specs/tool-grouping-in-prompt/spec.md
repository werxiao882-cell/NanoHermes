## ADDED Requirements

### Requirement: Deferred tools are grouped by toolset in system prompt
The PromptAssembler SHALL group deferred tools by their toolset when building the Tool Usage section. The grouping MUST be retrieved dynamically from ToolRegistry.get_tool_categories_with_info(), not hardcoded.

#### Scenario: Tools grouped by toolset
- **WHEN** building deferred tools section
- **THEN** output has subsections like `### <toolset>: <tool1>, <tool2>, ...` where tool names come from the registry

#### Scenario: Toolset header format
- **WHEN** a toolset has multiple tools
- **THEN** header format is `### <toolset>: <tool1>, <tool2>, ...`

#### Scenario: Single tool in toolset
- **WHEN** a toolset has only one tool
- **THEN** header format is `### <toolset>: <tool>`

### Requirement: Tool grouping uses ToolRegistry.get_tool_categories_with_info
The PromptAssembler SHALL use ToolRegistry.get_tool_categories_with_info() to retrieve tool grouping information, including toolset, name, description, and defer_loading status.

#### Scenario: Retrieving tool categories
- **WHEN** building tool usage section
- **THEN** PromptAssembler calls ToolRegistry.get_tool_categories_with_info() and filters for defer_loading=True tools

### Requirement: Deferred tools display loading hint
The Deferred Tools section SHALL include a hint indicating that tools must be discovered via search_tools before use.

#### Scenario: Loading hint display
- **WHEN** building deferred tools section
- **THEN** section header includes "(use search_tools to discover)" or similar hint

### Requirement: No hardcoded tool names in grouping logic
The PromptAssembler SHALL NOT contain any hardcoded tool names or toolset names. All tool information MUST come from the registry at assembly time.

#### Scenario: New tool automatically included
- **WHEN** a new deferred tool is registered with a new toolset
- **THEN** it appears in the system prompt under its toolset without any code changes to PromptAssembler
