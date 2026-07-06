---
name: tool-orchestration-dfx
category: software-development
description: Production-grade tool orchestration patterns — error classification, retry with backoff, concurrency control, result budgeting, execution state tracking.
trigger: When designing, implementing, or debugging tool orchestration, tool reliability, error handling, retry logic, concurrency control, or context budgeting in an AI agent system. Also when analyzing external agent codebases (Claude Code, etc.) for reliability patterns.
---

# Tool Orchestration DFX (Design for Excellence)

Patterns for production-grade tool execution in AI agent systems: error classification, retry with backoff, concurrency control, result budgeting, and execution state tracking.

## Core Principles

1. **Fail-closed by default**: Unknown errors → no retry. Only explicitly retryable errors get retried.
2. **Read-only tools are retryable**: `read_file`, `search_files`, `skill_view` have no side effects and can safely retry.
3. **Write/execute tools are NOT retryable**: `write_file`, `patch`, `terminal` may have already executed — retrying causes duplicate side effects.
4. **Exponential backoff + jitter**: Prevents thundering herd when multiple tools fail simultaneously.
5. **Head-tail truncation**: When tool output exceeds context budget, preserve head (errors/diagnosis) + tail (summary/errors), truncate middle.

## Error Classification (Reference: Claude Code `withRetry.ts`, 822 lines)

Classify errors into 4 categories with distinct recovery actions:

| Error Pattern | Classification | Action | Backoff |
|---|---|---|---|
| `ECONNRESET`, `EPIPE`, `Connection refused`, `Timeout` | Retryable | reconnect | base * 2^attempt |
| `401`, `Unauthorized`, `token expired` | Retryable | refresh_credentials | base (no backoff) |
| `429`, `529`, `rate limit`, `overloaded` | Retryable | backoff | base * 2^attempt * 2 (doubled) |
| `ValueError`, `TypeError`, `PermissionError`, `FileNotFoundError` | Non-retryable | fail | N/A |

### Retry Configuration

```
BASE_DELAY_MS = 500
MAX_DELAY_MS = 60_000       # 60s cap
MAX_RETRIES = 3             # default for most tools
JITTER_RATIO = 0.5          # ±50% jitter
```

### Retry Flow

```
for attempt in 1..max_retries:
    try: result = executor()
    except error:
        classify error → (is_retryable, action, delay)
        if not retryable: return error
        apply recovery action (reconnect / refresh / backoff)
        sleep(delay + jitter)
```

## Concurrency Control (Reference: Claude Code `toolOrchestration.ts`)

### Partition Tool Calls

Consecutive concurrency-safe tools merge into one batch → `asyncio.gather()` parallel execution. Non-safe tools execute serially.

```python
# Pseudo-code partitioning
batches = []
for call in tool_calls:
    is_safe = tool.is_concurrency_safe(call)
    if is_safe and batches[-1].is_concurrency_safe:
        batches[-1].calls.append(call)  # merge
    else:
        batches.append(Batch(is_safe, [call]))
```

### Two-Level Semaphore Control

1. **Global semaphore**: `max_tool_concurrency` (default 10) — limits ALL tools
2. **Per-tool semaphore**: `max_concurrent_instances` (default 1) — limits each tool
3. **Queue timeout**: 120s — if waiting for semaphore exceeds this, return error

### Tool Concurrency Defaults

| Tool | is_concurrency_safe | max_concurrent_instances |
|------|---------------------|-------------------------|
| read_file | True | 20 |
| search_files | True | 10 |
| terminal | False | 1 |
| write_file | False | 1 |
| patch | False | 1 |

## Result Budget

Prevents single tool output from consuming entire context window.

```
DEFAULT_BUDGET = 8000 tokens
TERMINAL_BUDGET = 4000 tokens  # terminal output is usually larger

Truncation strategy:
  head = 40% of budget
  tail = 40% of budget
  middle = "... [output truncated, ~N tokens omitted] ..."
```

**Why preserve tail?** Terminal error messages are usually at the end. File listings often have summary info at the bottom. Logs have key status in final lines.

## Execution State Tracking

Track tool lifecycle: `in_progress` → `completed` / `failed` / `timeout`

- Prevent re-entrance: same `tool_call_id` cannot execute twice simultaneously
- Auto-clean timed-out executions (default 300s)
- Keep recent history (last 100) for debugging and statistics

## Pitfalls

### 1. Don't retry write tools
Retrying `write_file` or `terminal` after a partial success causes duplicate writes or command re-execution. Only retry read-only tools.

### 2. Don't use `asyncio.run()` in a dispatch loop
If an event loop is already running (TUI, async framework), `asyncio.run()` will fail. Use thread-based isolation or `run_coroutine_threadsafe()`.

### 3. Token estimation without tokenizer
For result budget, use `chars * 0.75` as token estimate. Exact tokenization requires calling the LLM tokenizer which is expensive.

### 4. Jitter is critical
Without jitter, multiple failing tools retry at exactly the same time, causing a second wave of failures. Always add ±50% random jitter to backoff delays.

### 5. Context Modifier pattern
Tools that modify global state (e.g., `cd` changes working directory, `write_file` updates file attachments) should register context modifiers that are applied AFTER the entire batch completes — not mid-batch. This prevents inconsistent intermediate state.

## Related

- See `references/claude-code-dfx-analysis.md` for detailed Claude Code source analysis
- See `references/nanohermes-tool-architecture.md` for NanoHermes tool system structure
