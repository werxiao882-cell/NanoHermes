## ADDED Requirements

### Requirement: Provider Profile Registration
The system SHALL maintain a registry of provider profiles, each containing api_mode, base_url, env_vars priority list, and fallback_models.

#### Scenario: Register a new provider profile
- **WHEN** a provider profile is registered with id, api_mode, base_url, and env_vars
- **THEN** the profile is stored in the registry and retrievable by id

#### Scenario: Retrieve an existing provider profile
- **WHEN** getProviderProfile is called with a valid provider id
- **THEN** the corresponding ProviderProfile is returned

#### Scenario: List all registered providers
- **WHEN** listProviders is called
- **THEN** an array of all registered provider ids is returned

### Requirement: Provider Profile Structure
Each ProviderProfile SHALL contain: id (string), name (string), api_mode (string), base_url (string | null), env_vars (string[]), fallback_models ({provider, model}[]).

#### Scenario: Create a complete provider profile
- **WHEN** a ProviderProfile is created with all fields populated
- **THEN** all fields are accessible with correct types

### Requirement: Provider Alias Support
The system SHALL support provider aliases, mapping alternative names to canonical provider ids.

#### Scenario: Resolve alias to canonical id
- **WHEN** resolveProviderAlias is called with a known alias
- **THEN** the canonical provider id is returned

#### Scenario: Unknown alias returns null
- **WHEN** resolveProviderAlias is called with an unknown alias
- **THEN** null is returned
