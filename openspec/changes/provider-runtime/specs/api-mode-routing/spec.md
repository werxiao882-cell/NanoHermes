## ADDED Requirements

### Requirement: API Mode Detection
The system SHALL detect the api_mode from explicit argument, provider profile, or base_url heuristic, in that priority order.

#### Scenario: Explicit api_mode takes precedence
- **WHEN** api_mode is explicitly passed as constructor argument
- **THEN** that api_mode is used regardless of other sources

#### Scenario: Provider profile api_mode used as default
- **WHEN** no explicit api_mode is set but provider profile declares one
- **THEN** the profile api_mode is used

#### Scenario: Base URL heuristic for Anthropic
- **WHEN** base_url contains "api.anthropic.com" and no api_mode is set
- **THEN** api_mode defaults to "anthropic_messages"

#### Scenario: Default to chat_completions
- **WHEN** no explicit api_mode, profile mode, or heuristic match exists
- **THEN** api_mode defaults to "chat_completions"

### Requirement: Supported API Modes
The system SHALL support three api_mode values: "chat_completions", "anthropic_messages", "codex_responses".

#### Scenario: chat_completions mode uses OpenAI client
- **WHEN** api_mode is "chat_completions"
- **THEN** the OpenAI-compatible client is used with standard message format

#### Scenario: anthropic_messages mode uses Anthropic client
- **WHEN** api_mode is "anthropic_messages"
- **THEN** the Anthropic client is used with message format conversion

#### Scenario: Unknown api_mode throws error
- **WHEN** an unsupported api_mode is provided
- **THEN** an error is thrown listing supported modes

### Requirement: Client Type Selection
The api_mode SHALL determine which SDK client is instantiated.

#### Scenario: chat_completions creates OpenAI client
- **WHEN** api_mode is "chat_completions"
- **THEN** an openai.OpenAI client instance is created

#### Scenario: anthropic_messages creates Anthropic client
- **WHEN** api_mode is "anthropic_messages"
- **THEN** an Anthropic client instance is created
