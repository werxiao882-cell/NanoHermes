# NanoHermes Tool Architecture

Source: `/mnt/d/code/NanoHermes/src/tools/` — 17 registered tools.

## Tool Registry Pattern

Tools auto-register via `register_tool()` at module import time. Two initialization paths:
- `discover_tools(tools_dir)`: AST-based auto-discovery (dev)
- `init_all_tools()`: explicit import of all modules (prod)

## Tool Categories

### Always-Loaded (6 tools) — appear in initial LLM context
- `read_file`, `write_file`, `search_files`, `patch`, `terminal`, `search_tools`

### Deferred-Loading (11 tools) — discovered via `search_tools` on demand
- `execute_code`, `process`, `todo`, `memory`, `session_search`, `clarify`, `skill_view`, `skills_list`, `skill_manage`, `delegate_task`, `cronjob`

## Dispatcher Architecture (`dispatcher.py`, 399 lines)

### Async Bridge — 3 Strategies

1. **Strategy A**: Running loop exists → new thread + new event loop
   - Can't nest `run_until_complete()` in same thread
   - Can't `await` from synchronous dispatch()

2. **Strategy B**: No running loop → persistent global event loop
   - Lazy-loaded, thread-safe, daemon thread
   - `run_coroutine_threadsafe()` for task submission

3. **Strategy C**: Timeout protection (300s) on both paths

### Error Wrapping
All exceptions caught and returned as JSON error strings:
```json
{"error": "工具执行失败: ExceptionType: message"}
```

### Parameter Parsing
LLM returns `function_call.arguments` as JSON string. `_parse_args()` handles:
- `None` → `{}`
- `dict` → pass through
- `str` → `json.loads()`, wrap non-dict as `{"value": parsed}`
- Invalid JSON → `{"raw": original}`

## File Sizes

| Module | Lines | Purpose |
|--------|-------|---------|
| registry.py | ~600 | Tool registry, AST discovery, schema generation |
| dispatcher.py | 399 | Dispatch + async bridge |
| file_tool.py | ~500 | read_file/write_file/search_files/patch |
| terminal.py | ~350 | terminal + danger patterns + approval flow |
| tool_search.py | ~430 | BM25 + Regex dual-engine tool search |
| cronjob_tool.py | ~440 | Cron job management |
| delegation_tool.py | ~250 | Multi-agent delegation |
| memory_tool.py | ~290 | Memory system tool |

## Missing DFX (vs Claude Code)

| Capability | Status | Notes |
|------------|--------|-------|
| Error classification | ❌ Missing | All errors treated identically |
| Tool retry | ❌ Missing | No retry logic |
| Concurrency limiting | ❌ Missing | No semaphore control |
| Context modifiers | ❌ Missing | No post-execution context updates |
| Result budgeting | ⚠️ Partial | Some tools have `max_results`, no global budget |
| Execution tracking | ❌ Missing | No in-progress/completed state |
| Fast-mode cooldown | ❌ Missing | No rate-limit downgrade |
| Persistent retry | ❌ Missing | No unattended mode |
