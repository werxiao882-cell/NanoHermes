# Claude Code DFX Reference Analysis

## Source: withRetry.ts (822 lines, 29KB)

### Error Classification

```typescript
isTransientCapacityError()   → 429/529 → retry
isStaleConnectionError()     → ECONNRESET/EPIPE → reconnect
isOAuthTokenRevokedError()   → 403 → refresh token
isBedrockAuthError()         → Bedrock auth → refresh credentials
isFastModeCooldown()         → rate limit → degrade to standard mode
```

### Retry Strategy

| Parameter | Value | Purpose |
|-----------|-------|---------|
| DEFAULT_MAX_RETRIES | 10 | Max retries for foreground queries |
| BASE_DELAY_MS | 500 | Exponential backoff base |
| MAX_529_RETRIES | 3 | Max 529 errors before fallback |
| PERSISTENT_MAX_BACKOFF_MS | 5 min | Unattended mode max backoff |
| PERSISTENT_RESET_CAP_MS | 6 hours | Reset counter after 6h |
| HEARTBEAT_INTERVAL_MS | 30s | Keep-alive during persistent retry |

### Foreground Query Sources (retry on 529)

Only queries where the user IS blocking on the result retry on 529:
- `repl_main_thread` (and variants)
- `sdk`
- `agent:custom/default/builtin`
- `compact`, `hook_agent`, `hook_prompt`
- `verification_agent`, `side_question`
- `auto_mode`, `bash_classifier` (feature-gated)

Background queries (summaries, titles, suggestions, classifiers) bail immediately to avoid gateway amplification during capacity cascades.

### Fast Mode Degradation

On 429/529:
1. Short Retry-After → wait and retry with fast mode (preserve prompt cache)
2. Long/unknown Retry-After → enter cooldown, switch to standard speed model
3. Overage disabled → permanently disable fast mode

## Source: toolOrchestration.ts (188 lines, 5.7KB)

### Concurrency Partitioning

```typescript
function partitionToolCalls(toolUseMessages, context): Batch[] {
  // Groups consecutive concurrency-safe tools together
  // Non-safe tools get their own single-item batch
}
```

### Context Modifier Pattern

```typescript
// Tools return context modifiers that are queued and applied after batch completes
const queuedContextModifiers: Record<string, ((context) => context)[]> = {}
for await (const update of runToolsConcurrently(...)) {
  if (update.contextModifier) {
    queuedContextModifiers[update.toolUseID].push(update.contextModifier.modifyContext)
  }
}
// Apply all modifiers after batch completes
for (const block of blocks) {
  for (const modifier of queuedContextModifiers[block.id]) {
    currentContext = modifier(currentContext)
  }
}
```

### Max Concurrency

```typescript
function getMaxToolUseConcurrency(): number {
  return parseInt(process.env.CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY || '', 10) || 10
}
```

## Comparison: NanoHermes dispatcher.py (399 lines, 16.9KB)

### Current Capabilities

| Capability | Status | Notes |
|-----------|--------|-------|
| Error wrapping | ✅ | try/catch → JSON error string |
| Timeout protection | ✅ | 300s on both async bridge paths |
| Async bridge | ✅ | 3 strategies (new thread / persistent loop / running loop) |
| Availability check | ✅ | check_fn fast-fail |
| Dangerous command detection | ✅ | DANGEROUS_PATTERNS regex |
| Tool truncation | ⚠️ | Individual tools only (max_results, limit) |
| Compression circuit breaker | ✅ | advanced-compression spec |
| Model fallback | ✅ | fallback-chain spec |

### Missing Capabilities (confirmed via triple filter)

| Capability | Impact | Priority |
|-----------|--------|----------|
| Tool call retry | Transient failures go straight to error | High |
| Error classifier | All errors treated equally | High |
| Concurrency limiter | No upper bound on parallel tools | Medium |
| Context Modifier | Tools can't update global state | Medium |
| Result budget | Single tool can fill context window | Medium |
| Execution tracking | No visibility into running tools | Low |
| Fast mode degradation | No degradation strategy | Low |
| Persistent retry | No unattended mode support | Low |

## OpenSpec Proposals Created

1. `claude-code-gap-analysis` — 6 specs, 42 tasks
   - tool-concurrency-partitioning
   - tool-result-budget
   - context-modifier
   - headless-sdk-mode
   - trust-levels
   - mcp-engineering

2. `tool-dfx-reliability` — 4 specs, 30 tasks
   - tool-retry (error classification + exponential backoff with jitter)
   - tool-concurrency-limiter (Semaphore + per-tool override)
   - tool-result-budget (token-level truncation)
   - tool-execution-tracking (state tracking + dedup)
