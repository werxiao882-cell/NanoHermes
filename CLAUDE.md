# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NanoHermes is a self-evolving AI Agent system built in Python from scratch, inspired by Hermes Agent architecture. It features multi-provider LLM support, deferred tool loading with BM25+Regex search, session persistence (SQLite + JSONL), cross-session memory, context compression, multi-agent delegation, and a skill system.

## Key Commands

```bash
# Run the application
python -m src.main              # TUI interactive mode (default)
python -m src.main --debug      # Debug mode (full request/response JSON + thinking)
python -m src.main --resume     # Resume most recent session
python -m src.main --headless   # Headless REPL mode (no TUI, for pipes/SSH/CI)

# Run tests
python -m pytest tests/ -v              # All tests
python -m pytest tests/provider/ -v     # Single module tests
python -m pytest tests/tools/ -v
python -m pytest tests/test_e2e.py -v -s  # End-to-end tests (-s shows output)
python -m pytest tests/tools/test_search_tool.py::test_bm25_search -v  # Single test

# MCP server modes
python -m src.mcp.server                              # Stdio mode (default)
python -m src.mcp.server --transport streamable-http --port 8000  # HTTP mode
```

## Configuration

**Priority chain**: Explicit params > Project config (`./nanohermes.json`) > Global config (`~/.nanohermes/config.json`) > `.env` > Defaults

- `nanohermes.json`: Structure config (model, providers, TUI settings)
- `.env`: Secrets (API keys) - gitignored
- Data stored in `~/.nanohermes/` (sessions.db, sessions/*.jsonl, memory/)

## Architecture

### Core Loop

```
ConversationLoop (src/conversation/loop.py)
    │
    ├── Model calls via Provider Runtime
    ├── Tool dispatch via Dispatcher
    ├── Retry logic with error classification
    ├── Dynamic tool discovery (deferred loading)
    └── Compression triggers
```

### Module Boundaries

| Module | Responsibility |
|--------|----------------|
| `src/main.py` | Composition root - dependency injection only, no business logic |
| `src/conversation/` | Core loop, EventBus, chain interceptors, error classification, dynamic tool management |
| `src/provider/` | LLM provider runtime (credentials, API routing, client factory, fallback) |
| `src/tools/core/` | Registry, Dispatcher, BM25+Regex search engine |
| `src/tools/impls/` | Individual tool implementations (terminal, file, memory, etc.) |
| `src/session/` | SQLite + JSONL dual storage layer |
| `src/memory/` | Memory provider interface, file-based memory |
| `src/skills/` | SKILL.md parsing, Curator self-evolution |
| `src/compression/` | Context compression with summary budget |
| `src/prompt/` | Three-layer system prompt assembly (stable/context/volatile) |
| `src/cli/` | TUI chat interface, event handlers, streaming components |
| `src/hooks/` | Chain interceptors (dangerous command guard, ScriptHook, config loader) |
| `src/delegation/` | Multi-agent delegation (leaf/orchestrator roles) |
| `src/mcp/` | MCP protocol support (server/client/bridge) |

### Tool System - Deferred Loading

Tools are split into two categories:

**Always loaded** (`defer_loading=False`, 6 tools): Added to LLM context at startup
- `read_file`, `write_file`, `search_files`, `patch`, `terminal`, `search_tools`

**Deferred** (`defer_loading=True`, 11+ tools): Discovered via `search_tools` on demand
- `execute_code`, `process`, `todo`, `memory`, `session_search`, `clarify`, `skill_view`, `skills_list`, `skill_manage`, `delegate_task`, `cronjob`, etc.

The `search_tools` tool uses BM25 (natural language) + Regex (exact pattern) dual-engine with Auto mode that detects query characteristics to select strategy.

### Event-Driven Architecture

`ConversationLoop` publishes events via `EventBus`. External handlers (memory, TUI, debug) subscribe to events. This decouples the core loop from side effects.

**Chain of Responsibility Interceptors**: `EventBus.intercept()` registers interceptors that can modify data or block the chain. Interceptors use `(data, next_fn)` signature - calling `next_fn()` passes control, not calling it blocks. After the interceptor chain completes (blocked or not), observers still fire. `emit()` returns `ChainResult(blocked, message)`.

## Coding Conventions

### Language & Style

- **Code comments in Chinese** - explain "why" not just "what"
- Python >= 3.11, pytest with `asyncio_mode = "auto"` (no manual async markers needed)
- Each `src/<module>/` must include `ARCHITECTURE.md` documenting responsibilities, data flow, and design decisions

### Module Rules

- **Single file max 300 lines** - split by responsibility
- **Single function max 50 lines** - break into smaller functions
- **No cross-module direct calls** - use public APIs or EventBus
- **Chain interceptors** - `loop.events.intercept(EventType, handler, priority)` for data modification/blocking
- **Dependency injection** - objects receive dependencies via constructor, never create other module instances internally
- **Use `build_client()` factory** from `src/provider/client_factory.py` - never instantiate SDK clients directly in entry files

### Prohibited Patterns

```python
# WRONG: Creating SDK client directly
from openai import OpenAI
client = OpenAI(api_key=api_key)

# RIGHT: Use factory
from src.provider.client_factory import build_client
client = build_client(config)

# WRONG: Module creates its own dependencies
class TUIApp:
    def __init__(self):
        self.session_db = SessionDB(db_path)  # Should be injected

# RIGHT: Dependency injection
class TUIApp:
    def __init__(self, session_db: SessionDB):
        self.session_db = session_db
```

## OpenSpec Workflow

Changes are managed via OpenSpec (in `openspec/changes/<name>/`):

```bash
/opsx-explore          # Discuss architecture before coding
/opsx-propose <name>   # Create change proposal
/opsx-apply <name>     # Implement the change
/opsx-archive <name>   # Archive completed change
```

## Testing Notes

- Integration tests use **real LLM API calls**, not mocks - mocks miss toolchain integration bugs
- PTY-driven E2E tests simulate real user interaction via `terminal(pty=True, background=True)`
- End-to-end tests require valid API keys in `.env`
- Known skips: `tests/tools/test_code_execution_tool.py` (encoding issues)

### PTY Test Pattern

```
terminal(pty=True, background=True, command="python -m src.main")
process(action='wait', session_id='...', timeout=20)      # Wait for startup
process(action='submit', session_id='...', data="Hello")  # Send message
process(action='wait', session_id='...', timeout=60)      # Wait for response (60-120s for LLM)
process(action='submit', session_id='...', data="/quit")  # Graceful exit
```

## Key Files

- `src/main.py` - Entry point (composition root)
- `src/conversation/loop.py` - Core conversation loop
- `src/tools/core/registry.py` - Tool registration
- `src/tools/core/dispatcher.py` - Tool dispatch
- `src/tools/core/search_tool.py` - BM25+Regex search engine
- `src/provider/client_factory.py` - LLM client factory
- `nanohermes.example.json` - Full configuration example
- `AGENTS.md` - Detailed agent guidance
- `TESTING_GUIDE.md` - Integration test methodology
