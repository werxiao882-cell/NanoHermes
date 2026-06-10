## ADDED Requirements

### Requirement: ToolSearch builds BM25 index from tool definitions

The ToolSearch class SHALL build a BM25 inverted index from deferred tool definitions. The index SHALL tokenize tool names (split by `_` and `-`), descriptions, parameter names, and parameter descriptions. The index SHALL compute IDF values using the standard BM25 formula: `IDF(qi) = log((N - df + 0.5) / (df + 0.5))`.

#### Scenario: Build index from deferred tools
- **WHEN** ToolSearch is initialized with a list of deferred tools
- **THEN** a BM25 inverted index is built from all tool metadata

#### Scenario: Index handles empty tool list
- **WHEN** ToolSearch is initialized with an empty list
- **THEN** the index is empty and search returns no results

### Requirement: ToolSearch supports BM25 natural language search

The `search(query, mode="bm25")` method SHALL tokenize the query, compute BM25 scores for each tool, and return the top_k tools sorted by descending score. The default parameters SHALL be k1=1.5 and b=0.75.

#### Scenario: BM25 search returns relevant tools
- **WHEN** searching for "send a message to a user" with BM25 mode
- **THEN** tools with descriptions mentioning messaging or users rank highest

#### Scenario: BM25 search respects top_k limit
- **WHEN** searching with `top_k=3`
- **THEN** at most 3 tools are returned

### Requirement: ToolSearch supports Regex search

The `search(query, mode="regex")` method SHALL compile the query as a Python regular expression and match against tool names, descriptions, parameter names, and parameter descriptions. If the regex compilation fails, the method SHALL catch `re.error` and return an empty list.

#### Scenario: Regex matches tool names
- **WHEN** searching for `"get_.*_data"` with regex mode
- **THEN** all tools with names matching the pattern are returned

#### Scenario: Invalid regex returns empty results
- **WHEN** searching for an invalid regex pattern like `"[invalid"`
- **THEN** an empty list is returned without raising an exception

### Requirement: ToolSearch auto-selects search strategy

The `search(query, mode="auto")` method SHALL detect regex-like patterns in the query (presence of `.*`, `[]`, `()`, `^`, `$`, `+`, `?`, `|`) and use regex mode. Otherwise, it SHALL use BM25 mode.

#### Scenario: Auto detects regex pattern
- **WHEN** searching for `"(?i)slack"` with auto mode
- **THEN** regex mode is used

#### Scenario: Auto defaults to BM25
- **WHEN** searching for "send a message" with auto mode
- **THEN** BM25 mode is used
