## ADDED Requirements

### Requirement: Tool Availability Check Function
Each tool MAY provide a check_fn that returns true when the tool is available and false otherwise. Typical checks include API key presence, service running, or binary installed.

#### Scenario: Tool with passing check_fn is available
- **WHEN** a tool's check_fn returns true
- **THEN** the tool is included in the schema list

#### Scenario: Tool with failing check_fn is excluded
- **WHEN** a tool's check_fn returns false
- **THEN** the tool is excluded from the schema list

### Requirement: Check Result Caching
Check results SHALL be cached per call to avoid repeated env var reads or service probes. Multiple tools sharing the same check_fn only trigger one execution.

#### Scenario: Same check_fn called for multiple tools
- **WHEN** three tools share the same check_fn and getToolSchemas is called
- **THEN** the check_fn executes only once

### Requirement: Exception Treated as Unavailable
If a check_fn throws an exception, the tool SHALL be treated as unavailable.

#### Scenario: check_fn throws error
- **WHEN** a tool's check_fn throws an exception
- **THEN** the tool is excluded from the schema list and a warning is logged
