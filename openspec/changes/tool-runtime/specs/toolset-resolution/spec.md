## ADDED Requirements

### Requirement: Toolset Definition
The system SHALL maintain a TOOLSETS map where each key is a toolset name and the value is an array of tool names belonging to that toolset.

#### Scenario: Define a toolset
- **WHEN** a toolset is defined with a list of tool names
- **THEN** the toolset is stored and resolvable by name

### Requirement: Enabled/Disabled Toolset Resolution
The system SHALL resolve the active tool set based on enabled_toolsets (inclusive) or disabled_toolsets (exclusive) lists.

#### Scenario: Enabled toolsets filters to only listed
- **WHEN** enabled_toolsets is ["terminal", "file"]
- **THEN** only tools from those two toolsets are included

#### Scenario: Disabled toolsets excludes listed
- **WHEN** disabled_toolsets is ["browser"]
- **THEN** all toolsets except "browser" are included

#### Scenario: Neither enabled nor disabled includes all
- **WHEN** both enabled_toolsets and disabled_toolsets are null
- **THEN** all known toolsets are included

### Requirement: Toolset Expansion
The system SHALL expand toolset names to their constituent tool names, handling composite toolsets that reference other toolsets.

#### Scenario: Expand single toolset
- **WHEN** resolveToolset is called with "terminal"
- **THEN** the array of tool names in the terminal toolset is returned

#### Scenario: Legacy toolset name mapping
- **WHEN** a legacy toolset name like "terminal_tools" is used
- **THEN** it is mapped to the modern name "terminal"

### Requirement: Toolset Availability Check
Each toolset MAY have an associated check_fn that determines if the entire toolset is available.

#### Scenario: Toolset check passes
- **WHEN** a toolset's check_fn returns true
- **THEN** the toolset is considered available

#### Scenario: Toolset check fails
- **WHEN** a toolset's check_fn returns false
- **THEN** the toolset is excluded from resolution
