## ADDED Requirements

### Requirement: Define model configuration section

The config file SHALL include a `model` section specifying the primary LLM model to use. The section SHALL contain `provider` (string), `name` (string), and optionally `context_length` (integer). The provider value SHALL correspond to a registered provider ID.

#### Scenario: Minimal model configuration
- **WHEN** config contains `{"model": {"provider": "dashscope", "name": "qwen3.6-plus"}}`
- **THEN** the model is resolved as qwen3.6-plus via the dashscope provider

#### Scenario: Model with context length override
- **WHEN** config contains `{"model": {"provider": "openai", "name": "gpt-4o", "context_length": 64000}}`
- **THEN** the model uses a 64000 token context window instead of the default

### Requirement: Define provider configuration section

The config file SHALL include a `providers` section mapping provider IDs to their configuration. Each provider entry SHALL specify `base_url` (string) and `api_key_env` (string referencing an environment variable name).

#### Scenario: DashScope provider configuration
- **WHEN** config contains `{"providers": {"dashscope": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "api_key_env": "DASHSCOPE_API_KEY"}}}`
- **THEN** the dashscope provider uses the specified base URL and reads the API key from DASHSCOPE_API_KEY

#### Scenario: Multiple provider configurations
- **WHEN** config defines multiple providers (dashscope, openai, anthropic)
- **THEN** each provider has its own base_url and api_key_env configuration

### Requirement: Define MCP server configuration section

The config file SHALL include an `mcp` section with a `servers` array. Each server entry SHALL contain `name` (string), `transport` (string: "stdio" | "streamable_http" | "http_sse"), and transport-specific settings.

#### Scenario: Stdio MCP server configuration
- **WHEN** config contains a server with `"transport": "stdio"`
- **THEN** the server configuration SHALL include `command` (string) and `args` (array of strings)

#### Scenario: HTTP MCP server configuration
- **WHEN** config contains a server with `"transport": "streamable_http"`
- **THEN** the server configuration SHALL include `url` (string) and optionally `headers` (object)

#### Scenario: Empty MCP servers list
- **WHEN** config contains `"mcp": {"servers": []}`
- **THEN** no MCP servers are configured and the MCP client tool is inactive

### Requirement: Define TUI configuration section

The config file SHALL include a `tui` section with optional settings for the terminal interface. Supported fields SHALL include `typing_speed` (integer, milliseconds per character), `show_tool_panel` (boolean), and `tool_panel_position` (string: "left" | "right" | "bottom").

#### Scenario: Default TUI configuration
- **WHEN** the `tui` section is not present in config
- **THEN** defaults are used: typing_speed=10, show_tool_panel=true, tool_panel_position="right"

#### Scenario: Custom typing speed
- **WHEN** config contains `{"tui": {"typing_speed": 5}}`
- **THEN** the typewriter effect uses 5ms per character

### Requirement: Define auxiliary LLM configuration section

The config file SHALL include an `auxiliary` section for background task LLM settings. Supported fields SHALL include `provider` (string, "main" to reuse primary model), `model` (string), `max_tokens` (integer), and `temperature` (float).

#### Scenario: Auxiliary reuses main model
- **WHEN** config contains `{"auxiliary": {"provider": "main"}}`
- **THEN** the auxiliary client uses the same model and credentials as the primary model

#### Scenario: Auxiliary with separate model
- **WHEN** config contains `{"auxiliary": {"provider": "openai", "model": "gpt-4o-mini", "max_tokens": 2000}}`
- **THEN** the auxiliary client uses gpt-4o-mini with 2000 max tokens

### Requirement: Support minimal config file

The config file SHALL allow a minimal configuration with only the `model` section defined. All other sections SHALL use sensible defaults when omitted.

#### Scenario: Minimal valid config
- **WHEN** config contains only `{"model": {"provider": "dashscope", "name": "qwen3.6-plus"}}`
- **THEN** the system loads successfully with defaults for all other sections

#### Scenario: Empty config object
- **WHEN** config file contains `{}`
- **THEN** the system loads with all default values
