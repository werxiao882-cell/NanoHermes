## ADDED Requirements

### Requirement: Load configuration from JSON files

The system SHALL load configuration from JSON files at two locations: project-level `./nanohermes.json` and user-level `~/.nanohermes/config.json`. Project-level configuration SHALL override user-level configuration. If neither file exists, the system SHALL fall back to environment variables and default values.

#### Scenario: Both config files exist
- **WHEN** both `./nanohermes.json` and `~/.nanohermes/config.json` exist
- **THEN** project-level values override user-level values for the same keys
- **AND** user-level values are used for keys not present in project-level

#### Scenario: Only user-level config exists
- **WHEN** only `~/.nanohermes/config.json` exists
- **THEN** user-level configuration is used as the base

#### Scenario: No config files exist
- **WHEN** neither config file exists
- **THEN** the system falls back to environment variables and module defaults without error

#### Scenario: Invalid JSON in config file
- **WHEN** a config file contains invalid JSON
- **THEN** the system SHALL log a warning and skip that file, falling back to lower priority sources

### Requirement: Resolve configuration priority chain

The system SHALL resolve configuration values using a priority chain: explicit parameters > project config > user config > environment variables > module defaults. Each level SHALL only fill in values not provided by higher levels.

#### Scenario: Explicit parameter overrides config file
- **WHEN** a model name is passed as an explicit parameter AND also defined in config file
- **THEN** the explicit parameter value is used

#### Scenario: Config file overrides environment variable
- **WHEN** a model name is in config file AND MODEL_NAME env var is set
- **THEN** the config file value is used

#### Scenario: Environment variable used when no config
- **WHEN** no config file defines a model name AND MODEL_NAME env var is set
- **THEN** the environment variable value is used

#### Scenario: Default value used as last resort
- **WHEN** no source provides a value for typing_speed
- **THEN** the default value of 10 is used

### Requirement: Validate configuration against schema

The system SHALL validate loaded configuration against a defined schema. Invalid configurations SHALL produce clear error messages indicating which field failed validation and why.

#### Scenario: Valid configuration passes validation
- **WHEN** a config file contains all required fields with valid types
- **THEN** validation passes and configuration is loaded successfully

#### Scenario: Missing required field fails validation
- **WHEN** a config file is missing a required field
- **THEN** validation fails with an error message naming the missing field

#### Scenario: Invalid type fails validation
- **WHEN** a config field has an incorrect type (e.g., string instead of integer)
- **THEN** validation fails with an error message indicating the expected and actual types

### Requirement: Resolve API credentials from environment

The system SHALL resolve API keys and sensitive credentials from environment variables referenced in the config file using `_env` suffix notation. Credentials SHALL NOT be stored in config files.

#### Scenario: API key resolved from environment
- **WHEN** config specifies `"api_key_env": "DASHSCOPE_API_KEY"`
- **THEN** the system reads the API key from the DASHSCOPE_API_KEY environment variable

#### Scenario: Missing environment variable for credential
- **WHEN** the referenced environment variable is not set
- **THEN** the system SHALL produce an error indicating which credential is missing

### Requirement: Provide unified Config data class

The system SHALL provide a `Config` data class (Pydantic model) that represents the complete resolved configuration with typed fields for model, providers, MCP, TUI, and auxiliary settings.

#### Scenario: Config data class contains all sections
- **WHEN** configuration is loaded
- **THEN** the Config object contains model, providers, mcp, tui, and auxiliary sections

#### Scenario: Config data class provides defaults
- **WHEN** a section is not defined in any config source
- **THEN** the Config object contains default values for that section

### Requirement: Export resolved configuration for consumers

The system SHALL provide a `load_config()` function that returns a fully resolved and validated Config object. The function SHALL accept optional explicit parameters that override all other sources.

#### Scenario: Load config with no overrides
- **WHEN** `load_config()` is called with no arguments
- **THEN** configuration is resolved from files, env vars, and defaults

#### Scenario: Load config with explicit model override
- **WHEN** `load_config(model="gpt-4o")` is called
- **THEN** the model name is set to "gpt-4o" regardless of config file or env vars

#### Scenario: Load config with explicit API key
- **WHEN** `load_config(api_key="sk-xxx")` is called
- **THEN** the API key is set to "sk-xxx" regardless of environment variables
