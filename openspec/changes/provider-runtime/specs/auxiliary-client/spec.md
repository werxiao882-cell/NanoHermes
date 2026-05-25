## ADDED Requirements

### Requirement: Auxiliary Client Configuration
The system SHALL support configuring an auxiliary LLM client with its own provider, model, and max_tokens, independent of the main conversation model.

#### Scenario: Auxiliary client with explicit config
- **WHEN** auxiliary config specifies provider and model
- **THEN** those values are used for auxiliary tasks

#### Scenario: Auxiliary client falls back to main model
- **WHEN** auxiliary provider is set to "main"
- **THEN** the main conversation model is used for auxiliary tasks

### Requirement: Auxiliary Task Types
The auxiliary client SHALL support task types: compression, vision, memory_flush, session_search, skill_review.

#### Scenario: Compression task uses auxiliary config
- **WHEN** a compression summary is needed
- **THEN** the auxiliary client is used with compression-specific config

#### Scenario: Vision task uses auxiliary config
- **WHEN** a vision analysis is needed
- **THEN** the auxiliary client is used with vision-specific config

### Requirement: Auxiliary Client Reuses Provider Resolution
The auxiliary client SHALL use the same ProviderResolver and credential resolution as the main client.

#### Scenario: Auxiliary resolves to different provider
- **WHEN** auxiliary config specifies a different provider than main
- **THEN** credentials for that provider are resolved independently

### Requirement: Auxiliary Max Tokens Default
The auxiliary client SHALL enforce a configurable max_tokens default to prevent runaway token consumption.

#### Scenario: No max_tokens configured
- **WHEN** auxiliary call is made without max_tokens
- **THEN** a default max_tokens (e.g., 4000) is applied
