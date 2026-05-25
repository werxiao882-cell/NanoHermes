## ADDED Requirements

### Requirement: Fallback Chain Configuration
The system SHALL support configuring a fallback chain as an ordered list of {provider, model} pairs.

#### Scenario: Configure multiple fallback pairs
- **WHEN** fallback_providers is set to [{provider: "openai", model: "gpt-4o"}, {provider: "openrouter", model: "claude-sonnet"}]
- **THEN** fallback attempts occur in that order

#### Scenario: Empty fallback chain disables fallback
- **WHEN** fallback_providers is empty or not configured
- **THEN** no fallback is attempted on error

### Requirement: Fallback Activation Triggers
Fallback SHALL be attempted when the primary model encounters: non-retryable errors (401, 403, 404), max retries on transient errors (429, 500, 502, 503), or max retries on invalid responses.

#### Scenario: Fallback on 401 auth error
- **WHEN** the API returns 401 and fallback is configured
- **THEN** the first fallback provider is attempted

#### Scenario: Fallback on 429 after max retries
- **WHEN** 429 errors exceed the retry limit
- **THEN** fallback is attempted

### Requirement: One-Shot Fallback Activation
Once a fallback model is activated, it SHALL remain active for the rest of the conversation. The system SHALL NOT switch back to the primary model or try subsequent fallbacks.

#### Scenario: Fallback activated once
- **WHEN** the first fallback succeeds after primary failure
- **THEN** subsequent turns continue using the fallback model

#### Scenario: Fallback failure does not retry
- **WHEN** the activated fallback model also fails
- **THEN** the error is propagated (no further fallback attempts)

### Requirement: Fallback Client Rebuild
When fallback activates, the system SHALL rebuild the client with the new provider's credentials and configuration.

#### Scenario: Fallback to different provider rebuilds client
- **WHEN** fallback activates from anthropic to openai
- **THEN** the client is rebuilt with OpenAI credentials and base_url

### Requirement: Fallback State Tracking
The system SHALL track whether fallback has been activated to prevent re-activation.

#### Scenario: Check fallback_activated flag
- **WHEN** an error occurs after fallback has already activated
- **THEN** no further fallback is attempted
