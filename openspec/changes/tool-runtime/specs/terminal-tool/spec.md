## ADDED Requirements

### Requirement: Command Execution
The terminal tool SHALL execute shell commands using child_process.spawn, capturing stdout and stderr, and returning the combined output.

#### Scenario: Execute simple command
- **WHEN** the terminal tool executes "echo hello"
- **THEN** "hello" is returned in the output

#### Scenario: Command with non-zero exit code
- **WHEN** a command exits with non-zero status
- **THEN** the output includes the exit code and stderr content

### Requirement: Working Directory Override
The terminal tool SHALL support a cwd parameter to execute commands in a specific directory.

#### Scenario: Execute command in specific directory
- **WHEN** the terminal tool executes "pwd" with cwd set to "/tmp"
- **THEN** "/tmp" is returned in the output

### Requirement: Timeout Protection
The terminal tool SHALL enforce a configurable timeout (default 300 seconds). Commands exceeding the timeout are killed and an error is returned.

#### Scenario: Command exceeds timeout
- **WHEN** a command runs longer than the configured timeout
- **THEN** the process is killed and a timeout error is returned

### Requirement: Dangerous Command Detection
Before executing any command, the terminal tool SHALL check against a list of DANGEROUS_PATTERNS regex patterns covering destructive operations (rm -rf, mkfs, DROP TABLE, curl | sh, etc.).

#### Scenario: Dangerous command detected
- **WHEN** a command matches a dangerous pattern like "rm -rf /"
- **THEN** an approval request is returned instead of executing the command

#### Scenario: Safe command passes through
- **WHEN** a command does not match any dangerous pattern
- **THEN** the command is executed normally

### Requirement: Approval Flow
When a dangerous command is detected, the tool SHALL return a structured approval request that the caller can use to prompt the user.

#### Scenario: Return approval request
- **WHEN** a dangerous command is detected
- **THEN** the result contains {"requires_approval": true, "command": "...", "reason": "..."}
