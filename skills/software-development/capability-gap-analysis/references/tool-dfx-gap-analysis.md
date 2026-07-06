# Tool DFX Gap Analysis: Claude Code vs NanoHermes

Session: 2026-06-09. Compared Claude Code's tool orchestration DFX against NanoHermes.

## Reference Files Analyzed

| File | Lines | Key Content |
|------|-------|-------------|
| `withRetry.ts` | 822 (29KB) | Error classification, retry loops, exponential backoff, fast mode cooldown |
| `toolOrchestration.ts` | 188 (5.7KB) | partitionToolCalls(), contextModifier, concurrency control |
| `dispatcher.py` (NanoHermes) | 399 (16.9KB) | Basic try/catch, async bridge, no retry/concurrency limiting |

## Confirmed Gaps (Created OpenSpec: tool-dfx-reliability)

### 1. Tool Retry System
- **Claude**: `withRetry()` — 822 lines, 5 error categories, exponential backoff + jitter, max 10 retries
- **NanoHermes**: No retry — single attempt, error returned immediately
- **New specs**: `tool-retry/spec.md` (error classifier + retry manager + whitelist)

### 2. Concurrency Limiting
- **Claude**: `getMaxToolUseConcurrency()` → env var `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` (default 10), Promise.all with semaphore
- **NanoHermes**: No limit — all tools execute without concurrency control
- **New specs**: `tool-concurrency-limiter/spec.md` (asyncio.Semaphore + per-tool override)

### 3. Context Modifier
- **Claude**: Tools return `contextModifier`, applied after batch completes
- **NanoHermes**: No context modification after tool execution
- **New specs**: `claude-code-gap-analysis/specs/context-modifier/spec.md`

### 4. Tool Result Budget
- **Claude**: `applyToolResultBudget()` — token-level truncation, head+tail preservation
- **NanoHermes**: Individual tools have `max_results` but no unified budget
- **New specs**: `tool-result-budget/spec.md` + `claude-code-gap-analysis/specs/tool-result-budget/spec.md`

### 5. Execution State Tracking
- **Claude**: `setInProgressToolUseIDs()` / `markToolUseAsComplete()` — prevents re-entry
- **NanoHermes**: No execution state tracking
- **New specs**: `tool-execution-tracking/spec.md`

## New OpenSpec Files Created

```
openspec/changes/tool-dfx-reliability/
├── proposal.md
├── design.md
├── tasks.md (30 tasks)
└── specs/
    ├── tool-retry/spec.md (654 lines, detailed pseudo-code)
    ├── tool-concurrency-limiter/spec.md (491 lines)
    ├── tool-result-budget/spec.md (322 lines)
    └── tool-execution-tracking/spec.md (542 lines)

openspec/changes/claude-code-gap-analysis/ (6 additional gaps)
├── specs/tool-concurrency-partitioning/spec.md
├── specs/tool-result-budget/spec.md
├── specs/context-modifier/spec.md
├── specs/headless-sdk-mode/spec.md
├── specs/trust-levels/spec.md
└── specs/mcp-engineering/spec.md
```

Total: 4 new specs + 6 additional specs, 2009 lines of pseudo-code with implementation details.
