## ADDED Requirements

### Requirement: Detect Running Event Loop
The async bridge SHALL detect whether an event loop is already running in the current process and choose the appropriate execution path.

#### Scenario: No running event loop
- **WHEN** asyncBridge is called and no event loop is running
- **THEN** a persistent event loop is used to execute the async handler

#### Scenario: Running event loop detected
- **WHEN** asyncBridge is called and an event loop is already running
- **THEN** the handler is executed in a separate thread with asyncio.run()

### Requirement: Persistent Event Loop Reuse
When no event loop is running, the async bridge SHALL reuse a persistent event loop across calls to keep cached async clients alive.

#### Scenario: Multiple async calls reuse same loop
- **WHEN** asyncBridge is called three times in sequence
- **THEN** the same persistent event loop handles all three calls

### Requirement: Async Handler Execution
The async bridge SHALL accept an async function and its arguments, execute it, and return the result synchronously.

#### Scenario: Execute async handler
- **WHEN** asyncBridge is called with an async function
- **THEN** the function is executed and its return value is returned synchronously

#### Scenario: Async handler throws error
- **WHEN** the async function throws an exception
- **THEN** the exception is caught and returned as an error string
