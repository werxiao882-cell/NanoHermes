## ADDED Requirements

### Requirement: Skill dataclass includes trigger and skip fields
The Skill dataclass SHALL include optional `trigger` and `skip` fields, each being a list of strings defining when the skill should or should not be used.

#### Scenario: Skill with trigger and skip rules
- **WHEN** a SKILL.md contains `trigger` and `skip` fields in frontmatter
- **THEN** the loaded Skill object includes these fields as string lists

#### Scenario: Skill without trigger and skip rules
- **WHEN** a SKILL.md does not contain `trigger` or `skip` fields
- **THEN** the loaded Skill object has empty lists for these fields

### Requirement: SkillManager builds skill prompt with TRIGGER/SKIP format
The SkillManager.build_skill_prompt() method SHALL format each skill description to include TRIGGER and SKIP rules inline, following Claude Code style.

#### Scenario: Skill with rules formatted correctly
- **WHEN** building skill prompt for a skill with trigger/skip rules
- **THEN** the output includes `- name: description TRIGGER — rules... SKIP — rules...`

#### Scenario: Skill without rules uses simple description
- **WHEN** building skill prompt for a skill without trigger/skip rules
- **THEN** the output includes `- name: description` without TRIGGER/SKIP markers

### Requirement: TRIGGER rules use string containment matching
TRIGGER rules SHALL be evaluated using simple string containment (case-insensitive) against the user message and conversation context.

#### Scenario: Trigger matches user message
- **WHEN** user message contains text matching a trigger rule (case-insensitive)
- **THEN** the skill is considered applicable

#### Scenario: Trigger does not match
- **WHEN** user message contains no text matching any trigger rule
- **THEN** the skill is not applicable

### Requirement: SKIP rules override TRIGGER rules
If any SKIP rule matches the current context, the skill SHALL NOT be used regardless of TRIGGER matches.

#### Scenario: Skip overrides trigger
- **WHEN** both trigger and skip rules match
- **THEN** the skill is NOT applicable (skip takes precedence)
