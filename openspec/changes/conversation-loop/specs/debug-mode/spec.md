## ADDED Requirements

### Requirement: Debug Mode Output
The system SHALL support a debug mode that outputs the complete request sent to the model and the complete response received from the model, including tool execution results.

#### Scenario: Debug mode prints request details
- **WHEN** debug mode is enabled and a model call is made
- **THEN** the system prints iteration number, message count, each message role and truncated content, tool_call_id if present, tool_calls with name and arguments, and tool schemas if provided

#### Scenario: Debug mode prints response details
- **WHEN** debug mode is enabled and a model response is received
- **THEN** the system prints content (truncated if >500 chars), tool_calls with name and arguments, and token usage (input/output)

#### Scenario: Debug mode prints tool execution results
- **WHEN** debug mode is enabled and a tool is executed
- **THEN** the system prints tool name, arguments, and result (truncated if >300 chars)

#### Scenario: Debug mode disabled by default
- **WHEN** ConversationLoop is created without debug parameter
- **THEN** debug mode is False and no request/response details are printed

### Requirement: Debug Mode CLI Flag
The system SHALL support a `--debug` command line flag to enable debug mode in interactive mode.

#### Scenario: --debug flag enables debug mode
- **WHEN** the user runs `python -m src.main --debug`
- **THEN** debug mode is enabled and request/response details are printed

#### Scenario: Without --debug flag debug mode is off
- **WHEN** the user runs `python -m src.main` without --debug
- **THEN** debug mode is disabled and no debug output is shown
