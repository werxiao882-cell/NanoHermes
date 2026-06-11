## ADDED Requirements

### Requirement: ConversationLoop merges discovered tools each iteration

The ConversationLoop SHALL maintain a `_discovered_tools` dictionary mapping tool names to their schemas. Before each model call, the loop SHALL merge `_always_loaded_schemas` with `_discovered_tools.values()` to produce the current tool set passed to the model.

#### Scenario: Initial turn has only always-loaded tools
- **WHEN** the first iteration calls the model
- **THEN** only always-loaded schemas are passed (discovered tools are empty)

#### Scenario: Discovered tools are merged in subsequent turns
- **WHEN** tools have been discovered and a new iteration starts
- **THEN** the model receives always-loaded schemas plus discovered tool schemas

### Requirement: search_tools result auto-discovers tools

When the dispatched tool call is `search_tools`, the ConversationLoop SHALL parse the JSON result, extract tool schemas, and add each to `_discovered_tools` keyed by tool name. The tool result SHALL still be appended as a tool message for the model.

#### Scenario: Search results are added to discovered tools
- **WHEN** search_tools returns 3 tool schemas
- **THEN** all 3 schemas are added to `_discovered_tools`

#### Scenario: Duplicate discovered tools are overwritten
- **WHEN** search_tools returns a tool already in `_discovered_tools`
- **THEN** the existing entry is overwritten with the new schema

### Requirement: Discovered tools are available for immediate use

Tools added to `_discovered_tools` during iteration N SHALL be available in the tool set for iteration N+1, allowing the model to call them in the next turn.

#### Scenario: Model can call discovered tool next turn
- **WHEN** search_tools discovers "github_create_pr" in iteration 1
- **THEN** the model can call "github_create_pr" in iteration 2
