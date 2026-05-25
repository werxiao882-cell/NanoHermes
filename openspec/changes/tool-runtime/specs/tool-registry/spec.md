## ADDED Requirements

### Requirement: Tool Registration
The system SHALL provide a registry.register() function that accepts name, toolset, schema, handler, and optional check_fn. Each call stores a ToolEntry keyed by name.

#### Scenario: Register a new tool
- **WHEN** registry.register is called with a unique name, toolset, schema, and handler
- **THEN** the tool is stored and retrievable by name

#### Scenario: Duplicate name logs warning and overwrites
- **WHEN** registry.register is called with a name that already exists
- **THEN** a warning is logged and the new entry replaces the old one

### Requirement: Tool Discovery
The system SHALL scan a tools directory for .ts files, detect which ones contain top-level registry.register() calls via AST parsing, and dynamically import them.

#### Scenario: Discover and import tool modules
- **WHEN** discoverTools is called on a directory containing tool files
- **THEN** each file with a top-level register() call is imported

#### Scenario: Skip non-tool files
- **WHEN** discoverTools encounters __init__.ts, registry.ts, or helper files without register() calls
- **THEN** those files are not imported

### Requirement: Tool Retrieval
The system SHALL provide getTool(name) to retrieve a single tool entry and getAllTools() to retrieve all entries.

#### Scenario: Get existing tool by name
- **WHEN** getTool is called with a registered tool name
- **THEN** the corresponding ToolEntry is returned

#### Scenario: Get non-existent tool returns null
- **WHEN** getTool is called with an unregistered name
- **THEN** null is returned

### Requirement: Tool Schema Collection
The system SHALL provide getToolSchemas(toolsetFilter) that returns OpenAI-format tool schemas, filtered by toolset and availability.

#### Scenario: Get all tool schemas
- **WHEN** getToolSchemas is called with no filter
- **THEN** schemas for all registered tools are returned

#### Scenario: Get schemas for specific toolset
- **WHEN** getToolSchemas is called with a toolset name
- **THEN** only schemas belonging to that toolset are returned
