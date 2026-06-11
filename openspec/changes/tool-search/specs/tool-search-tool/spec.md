## ADDED Requirements

### Requirement: search_tools tool is always visible

A tool named `search_tools` SHALL be registered with `defer_loading=False`, ensuring it is always visible to the model in every conversation turn. The tool SHALL accept `query` (string, required) and `mode` (string, optional, default "auto") parameters.

#### Scenario: search_tools is in initial schemas
- **WHEN** `get_tool_schemas(exclude_deferred=True)` is called
- **THEN** the `search_tools` schema is included in the result

#### Scenario: search_tools accepts query parameter
- **WHEN** the model calls `search_tools` with `{"query": "send email", "mode": "auto"}`
- **THEN** the tool executes the search and returns matching tool schemas

### Requirement: search_tools returns JSON-encoded tool schemas

The search_tools handler SHALL invoke ToolSearch with the provided query and mode, and return a JSON string containing an array of tool schemas (matching the OpenAI function tool format: `{name, description, parameters}`).

#### Scenario: Successful search returns schemas
- **WHEN** search_tools is called with a valid query
- **THEN** a JSON array of 0-5 tool schemas is returned

#### Scenario: No matches returns empty array
- **WHEN** search_tools is called with a query matching no tools
- **THEN** a JSON string `"[]"` is returned

#### Scenario: Search results are limited to top_k
- **WHEN** search_tools finds more than 5 matching tools
- **THEN** only the top 5 most relevant tools are returned
