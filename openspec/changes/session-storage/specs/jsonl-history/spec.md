## ADDED Requirements

### Requirement: JSONL Session History Storage
The system SHALL store complete session history in JSONL format, with one JSON object per line, supporting append-only writes and full session recovery.

#### Scenario: Append message to JSONL file
- **WHEN** a message is appended to a session
- **THEN** a JSON line containing role, content, timestamp, and optional metadata is written to {session_id}.jsonl

#### Scenario: Load messages from JSONL file
- **WHEN** load_messages is called with a valid session_id
- **THEN** all messages are returned in chronological order as a list of dicts

#### Scenario: Handle corrupted JSONL lines
- **WHEN** a JSONL file contains malformed JSON lines
- **THEN** corrupted lines are skipped and valid lines are still returned

#### Scenario: List all sessions
- **WHEN** list_sessions is called
- **THEN** an array of session IDs (derived from .jsonl filenames) is returned

### Requirement: Session Resume Command
The system SHALL support resuming a historical session via CLI command, loading the complete message history from JSONL and continuing the conversation.

#### Scenario: Resume session by ID
- **WHEN** the user runs `python -m src.main --resume <session_id>`
- **THEN** the system loads the session's JSONL history and continues the conversation with the loaded messages

#### Scenario: Resume session by title
- **WHEN** the user runs `python -m src.main --resume-title "My Session"`
- **THEN** the system finds the most recent session with that title and resumes it

#### Scenario: Resume most recent session
- **WHEN** the user runs `python -m src.main --resume` without arguments
- **THEN** the system resumes the most recently active session

#### Scenario: Resume non-existent session
- **WHEN** the user tries to resume a session that doesn't exist
- **THEN** an error message is displayed and a new session is created

### Requirement: Session History Integration with CLI
The streaming CLI SHALL integrate JSONL history storage, automatically appending each message and supporting session recovery.

#### Scenario: CLI appends user messages to JSONL
- **WHEN** the user sends a message in CLI mode
- **THEN** the message is appended to the session's JSONL file

#### Scenario: CLI appends assistant responses to JSONL
- **WHEN** the model returns a response in CLI mode
- **THEN** the response (including reasoning and tool calls) is appended to the session's JSONL file

#### Scenario: CLI loads history on resume
- **WHEN** the CLI starts with --resume flag
- **THEN** the session's JSONL history is loaded and displayed before accepting new input
