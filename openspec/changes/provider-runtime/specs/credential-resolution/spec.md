## ADDED Requirements

### Requirement: Credential Resolution Chain
The system SHALL resolve credentials by checking env_vars in priority order, returning the first non-empty value found.

#### Scenario: Resolve credential from primary env var
- **WHEN** the primary environment variable is set
- **THEN** its value is returned as the credential

#### Scenario: Fall back to secondary env var
- **WHEN** the primary env var is empty but secondary is set
- **THEN** the secondary env var value is returned

#### Scenario: All env vars empty throws error
- **WHEN** none of the configured env_vars are set
- **THEN** a descriptive error is thrown listing which variables are missing

### Requirement: Base URL Resolution
The system SHALL resolve base_url from config override, provider profile default, or env var, in that priority order.

#### Scenario: Config override takes precedence
- **WHEN** a base_url is explicitly provided in config
- **THEN** that value is used regardless of profile default

#### Scenario: Provider profile default used when no config
- **WHEN** no config base_url is set but provider profile has one
- **THEN** the profile base_url is used

### Requirement: Credential Source Tracking
The resolved credential SHALL include a source field indicating where it came from: "env", "config", "auth-store", or "explicit".

#### Scenario: Credential from environment variable
- **WHEN** credential is resolved from an env var
- **THEN** source is "env"

#### Scenario: Credential from explicit config
- **WHEN** credential is passed directly in config
- **THEN** source is "explicit"

### Requirement: API Key Isolation
The system SHALL NOT send a provider's API key to a different provider's base_url. Each key is bound to its declared endpoint.

#### Scenario: OpenRouter key not sent to custom endpoint
- **WHEN** resolving credentials for a custom endpoint
- **THEN** OPENROUTER_API_KEY is not considered as a candidate
