## ADDED Requirements

### Requirement: Debug Mode Output
The system SHALL support a debug mode that outputs the complete request body (JSON) sent to the model, the complete response body (JSON) received from the model, the model's reasoning/thinking content, and tool execution results.

#### Scenario: Debug mode prints request body as JSON
- **WHEN** debug mode is enabled and a model call is made
- **THEN** the system prints the complete request body as formatted JSON including messages array and tools array if provided

#### Scenario: Debug mode prints response body as JSON
- **WHEN** debug mode is enabled and a model response is received
- **THEN** the system prints the complete response body as formatted JSON (using model_dump() or string representation)

#### Scenario: Debug mode prints reasoning content
- **WHEN** debug mode is enabled and the model returns reasoning/thinking content
- **THEN** the system prints the reasoning content before the response body

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

### Requirement: Model Caller Returns Reasoning and Raw Response
The model caller function SHALL return reasoning content and raw response body in addition to content, tool_calls, and usage.

#### Scenario: Model caller returns reasoning from message.reasoning
- **WHEN** the model response has a reasoning attribute
- **THEN** the reasoning content is included in the returned dict

#### Scenario: Model caller returns reasoning from message.reasoning_content
- **WHEN** the model response has a reasoning_content attribute (Qwen format)
- **THEN** the reasoning content is included in the returned dict

#### Scenario: Model caller returns raw_response
- **WHEN** the model caller completes successfully
- **THEN** the raw response body (via model_dump() or str()) is included in the returned dict

#### Scenario: Model caller returns request_body
- **WHEN** the model caller completes successfully
- **THEN** the request body sent to the API is included in the returned dict
