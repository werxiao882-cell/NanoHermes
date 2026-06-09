## ADDED Requirements

### Requirement: ToolSearch supports select syntax for explicit tool loading
The ToolSearch class SHALL parse queries starting with `select:` prefix and return exact tool schemas by name, supporting comma-separated multiple tool names.

#### Scenario: Single tool selection
- **WHEN** query is `select:terminal`
- **THEN** ToolSearch returns exactly one tool schema with name `terminal`

#### Scenario: Multiple tool selection
- **WHEN** query is `select:terminal,read_file,write_file`
- **THEN** ToolSearch returns exactly three tool schemas in the order specified

#### Scenario: Non-existent tool in selection
- **WHEN** query is `select:terminal,nonexistent_tool`
- **THEN** ToolSearch returns only the existing tool schema for `terminal`, ignoring non-existent names

#### Scenario: Empty selection
- **WHEN** query is `select:`
- **THEN** ToolSearch returns empty array

#### Scenario: Fallback to BM25 for non-select queries
- **WHEN** query is `read a file` (no `select:` prefix)
- **THEN** ToolSearch uses BM25 search as before

#### Scenario: Fallback to Regex for pattern queries
- **WHEN** query is `get_.*_data` (regex pattern, no `select:` prefix)
- **THEN** ToolSearch uses Regex search as before

### Requirement: search_tools function passes select queries to ToolSearch
The `search_tools()` function SHALL pass the query directly to ToolSearch, which handles select syntax detection and processing.

#### Scenario: search_tools with select query
- **WHEN** model calls `search_tools(query="select:execute_code")`
- **THEN** search_tools returns JSON array with execute_code schema

### Requirement: Maximum tool selection limit
The select syntax SHALL support loading at most 10 tools in a single query to prevent context overflow.

#### Scenario: Exceeding selection limit
- **WHEN** query is `select:tool1,tool2,tool3,tool4,tool5,tool6,tool7,tool8,tool9,tool10,tool11`
- **THEN** ToolSearch returns only the first 10 tools and ignores the rest
