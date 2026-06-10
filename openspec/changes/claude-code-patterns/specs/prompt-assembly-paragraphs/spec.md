## ADDED Requirements

### Requirement: System prompt uses paragraph-based assembly structure
The PromptAssembler SHALL assemble system prompt using a paragraph-based structure following Claude Code style, with clearly defined sections in a specific order.

#### Scenario: Complete prompt assembly
- **WHEN** building system prompt with all components
- **THEN** the output contains sections in order: Identity → Tool Usage → Skills → Operational Guidance → Memory Context → User Profile → Current Time

### Requirement: All prompt content is dynamically assembled, not hardcoded
The PromptAssembler SHALL NOT hardcode any tool names, skill names, or groupings. All content MUST be retrieved from the ToolRegistry, SkillManager, or other data sources at assembly time.

#### Scenario: Tool list from registry
- **WHEN** building the Tool Usage section
- **THEN** tool names and descriptions are retrieved from ToolRegistry.get_tool_schemas() and ToolRegistry.get_tool_categories_with_info()

#### Scenario: Skills from skill manager
- **WHEN** building the Skills section
- **THEN** skill names and trigger/skip rules are retrieved from SkillManager.get_enabled_skills()

#### Scenario: No hardcoded tool names in assembler code
- **WHEN** reviewing the PromptAssembler source code
- **THEN** there are no hardcoded tool names like "terminal", "read_file", etc. in the assembly logic

### Requirement: Tool Usage section has subsections
The Tool Usage section SHALL contain three subsections: Always-Loaded Tools, Deferred Tools (grouped by toolset), and Tool Selection Guidelines.

#### Scenario: Always-Loaded Tools subsection
- **WHEN** building Tool Usage section
- **THEN** it lists tools from ToolRegistry.get_tool_schemas(exclude_deferred=True)

#### Scenario: Deferred Tools grouped by toolset
- **WHEN** building Tool Usage section
- **THEN** deferred tools are grouped under their toolset from ToolRegistry.get_tool_categories_with_info() filtered by defer_loading=True

#### Scenario: Tool Selection Guidelines
- **WHEN** building Tool Usage section
- **THEN** it includes generic guidelines that do not reference specific tool names

### Requirement: Skills section includes TRIGGER/SKIP inline
The Skills section SHALL format each active skill with its TRIGGER and SKIP rules inline, not as separate blocks.

#### Scenario: Skill with rules in Skills section
- **WHEN** building Skills section for a skill with trigger/skip
- **THEN** output is `- name: description TRIGGER — when... SKIP — when...`

### Requirement: Section separators use double newlines
Each major section SHALL be separated by double newlines (`\n\n`) to maintain markdown readability.

#### Scenario: Section separation
- **WHEN** assembling full prompt
- **THEN** each section is separated by exactly `\n\n`

### Requirement: Stable layer sections remain cacheable
The Identity, Tool Usage, Skills, and Operational Guidance sections SHALL remain in the stable layer for Anthropic prompt caching.

#### Scenario: Cache marker placement
- **WHEN** applying cache control
- **THEN** the last stable section (Operational Guidance) is marked as cache breakpoint
