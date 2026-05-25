## ADDED Requirements

### Requirement: Chat Completion Call
The system SHALL support making a chat completion call with messages, tools, and model parameters.

#### Scenario: Successful chat completion
- **WHEN** a chat completion is called with valid messages and model
- **THEN** the response contains content, usage (token counts), and finish reason

#### Scenario: Chat completion with tool schemas
- **WHEN** tool schemas are provided to the call
- **THEN** the response may include tool_calls in addition to or instead of text content

### Requirement: Streaming Response
The system SHALL support streaming responses via SSE or similar protocol, yielding tokens as they are generated.

#### Scenario: Stream yields tokens incrementally
- **WHEN** streaming is enabled
- **THEN** tokens are yielded one at a time as the model generates them

#### Scenario: Stream includes final usage data
- **WHEN** a stream completes
- **THEN** the final chunk includes token usage and finish reason

### Requirement: Interruptible API Call
The system SHALL support interrupting an in-flight API call without crashing the process.

#### Scenario: Interrupt during API call
- **WHEN** an API call is in progress and interrupt() is called
- **THEN** the call is abandoned and a controlled error is returned

#### Scenario: Interrupt does not corrupt client state
- **WHEN** an API call is interrupted
- **THEN** the client remains usable for subsequent calls

### Requirement: Token Usage Extraction
The system SHALL extract input_tokens, output_tokens, cache_read_tokens, and cache_write_tokens from every response.

#### Scenario: Extract usage from standard response
- **WHEN** a response is received with usage data
- **THEN** all four token counts are extracted (zero if not present)

### Requirement: Error Classification
The system SHALL classify API errors into categories: auth (401/403), rate_limit (429), context_overflow, billing (402), server_error (5xx), network_error.

#### Scenario: 401 classified as auth error
- **WHEN** the API returns 401
- **THEN** the error is classified as "auth"

#### Scenario: 429 classified as rate_limit
- **WHEN** the API returns 429
- **THEN** the error is classified as "rate_limit"

#### Scenario: 500 classified as server_error
- **WHEN** the API returns 500
- **THEN** the error is classified as "server_error"
