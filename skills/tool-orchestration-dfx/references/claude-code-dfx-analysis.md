# Claude Code DFX Source Analysis

Source: `claude-code-analysis/` directory in NanoHermes project (shareAI-lab/learn-claude-code analysis).

## Key Files

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `withRetry.ts` | 822 | 29KB | Error classification + retry + backoff + fast-mode cooldown |
| `toolOrchestration.ts` | 188 | 5.7KB | Tool partition + concurrent execution + context modifiers |
| `tokenBudget.ts` | 70 | 2.7KB | Token budget tracking |
| `modifiers.ts` | ~30 | 1.1KB | Context modifier utilities |
| `timeouts.ts` | ~40 | 1.4KB | Timeout utilities |

## withRetry.ts — Retry Architecture

### Error Classification Functions

```typescript
isTransientCapacityError(error) → 429/529 → retry
isStaleConnectionError(error)   → ECONNRESET/EPIPE → reconnect
isOAuthTokenRevokedError(error) → 403 → refresh token
isBedrockAuthError(error)       → Bedrock auth → refresh credentials
isFastModeCooldown()            → rate limit → downgrade to standard mode
```

### Retry Constants

```typescript
DEFAULT_MAX_RETRIES = 10
BASE_DELAY_MS = 500
MAX_529_RETRIES = 3
PERSISTENT_MAX_BACKOFF_MS = 5 * 60 * 1000  // 5 minutes
HEARTBEAT_INTERVAL_MS = 30_000              // 30s keep-alive
```

### Foreground vs Background Retry

- Foreground queries (user blocking on result): retry on 529
- Background queries (summaries, titles, suggestions): bail immediately
- New sources default to no-retry — only add to FOREGROUND_529_RETRY_SOURCES if user is waiting

### Persistent Retry Mode (Unattended)

```typescript
CLAUDE_CODE_UNATTENDED_RETRY=true → indefinite retries with higher backoff
PERSISTENT_MAX_BACKOFF_MS = 5min
PERSISTENT_RESET_CAP_MS = 6 hours
HEARTBEAT_INTERVAL_MS = 30s (keep-alive to prevent idle disconnect)
```

## toolOrchestration.ts — Concurrency Architecture

### Partition Logic

```typescript
function partitionToolCalls(toolUseMessages, context): Batch[] {
  return toolUseMessages.reduce((acc, toolUse) => {
    const isSafe = tool.isConcurrencySafe(input)
    if (isSafe && acc[acc.length-1]?.isConcurrencySafe) {
      acc[acc.length-1].blocks.push(toolUse)  // merge into existing batch
    } else {
      acc.push({ isConcurrencySafe: isSafe, blocks: [toolUse] })
    }
    return acc
  }, [])
}
```

### Concurrent Execution

```typescript
for await (const update of runToolsConcurrently(blocks, ...)) {
  if (update.contextModifier) {
    queuedContextModifiers[toolUseID].push(modifyContext)
  }
  yield { message: update.message, newContext: currentContext }
}
// Apply modifiers AFTER batch completes
for (const block of blocks) {
  for (const modifier of queuedContextModifiers[block.id]) {
    currentContext = modifier(currentContext)
  }
}
```

### Concurrency Control

```typescript
function getMaxToolUseConcurrency(): number {
  return parseInt(
    process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10
  ) || 10
}
```

## Context Modifier Pattern

Tools return a `contextModifier` function that modifies the global `ToolUseContext`. The modifier is queued during concurrent execution and applied after the batch completes.

Common modifier types:
- File attachment updates (after write_file/patch)
- Working directory changes (after cd commands)
- Available tools changes (dynamic tool discovery)
- Environment variable changes
