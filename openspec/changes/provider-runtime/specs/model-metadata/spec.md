## ADDED Requirements

### Requirement: Model Context Length Registry
The system SHALL maintain a registry mapping model identifiers to their context lengths in tokens.

#### Scenario: Look up known model context length
- **WHEN** getContextLength is called with a known model id
- **THEN** the correct context length is returned

#### Scenario: Unknown model returns default
- **WHEN** getContextLength is called with an unknown model id
- **THEN** a safe default (e.g., 8192) is returned

### Requirement: Model Pricing Data
The system SHALL store pricing data per model: input price per 1M tokens, output price per 1M tokens, cache read price, cache write price.

#### Scenario: Calculate cost from usage data
- **WHEN** cost calculation is requested with input_tokens, output_tokens, and model
- **THEN** the total USD cost is computed using the model's pricing data

#### Scenario: Unknown model pricing uses defaults
- **WHEN** cost calculation is requested for a model with no pricing data
- **THEN** a safe default pricing is used (or zero if conservative mode)

### Requirement: Context Length Used for Compression Thresholds
The model context length SHALL be used to determine when context compression is needed (e.g., >50% of context window).

#### Scenario: Check if compression needed
- **WHEN** conversation token count exceeds 50% of model context length
- **THEN** compression is triggered before the next API call
