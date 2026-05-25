## ADDED Requirements

### Requirement: Tool Dispatch by Name
The system SHALL provide dispatch(name, args) that looks up a tool by name, executes its handler with the provided arguments, and returns the result.

#### Scenario: Dispatch existing tool
- **WHEN** dispatch is called with a registered tool name and valid args
- **THEN** the tool's handler is executed and the result is returned

#### Scenario: Dispatch non-existent tool returns error
- **WHEN** dispatch is called with an unregistered tool name
- **THEN** a JSON error string is returned indicating tool not found

### Requirement: Error Wrapping
All tool execution SHALL be wrapped in try/catch at the dispatch level. Any exception results in a JSON error string: {"error": "Tool execution failed: ExceptionType: message"}.

#### Scenario: Handler throws exception
- **WHEN** a tool handler throws an error during execution
- **THEN** dispatch returns a JSON error string with the exception details

#### Scenario: Handler returns successfully
- **WHEN** a tool handler returns a result string
- **THEN** the result is returned as-is

### Requirement: Handler Argument Mapping
The dispatch function SHALL map the args object to the handler's expected parameters.

#### Scenario: Args passed as object
- **WHEN** dispatch is called with {param1: "value1", param2: 42}
- **THEN** the handler receives these values as its arguments

### Requirement: task_id Propagation
The dispatch function SHALL propagate task_id to handlers that accept it, for logging and session correlation.

#### Scenario: Dispatch with task_id
- **WHEN** dispatch is called with a task_id parameter
- **THEN** the handler receives task_id in its kwargs
