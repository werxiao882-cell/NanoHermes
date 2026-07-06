# NanoHermes Test Suite Fix Log + Integration Test Report

## Unit Test Fixes (Session: 2026-03-29)

Fixed ~45 failures/errors → 977 passed, 0 failed.

### Round 1: Dependencies + Syntax Errors
- Installed missing: `anthropic`, `mcp` (pip)
- Fixed `test_todo_e2e_real.py`: 4 corrupted Chinese characters (replacement char ``)
- Renamed conflicting test files: `test_engine.py`, `test_client.py`, `test_registry.py`, `test_integration.py`

### Round 2: Import Path Errors
- `AuxiliaryConfig` imported from wrong module → `src.config.models`

### Round 3: Field/Parameter Name Mismatches
- `messages[0]["type"]` → `messages[0]["role"]` (JSONL storage uses "role")
- `hermes_home/"MEMORY.md"` → `hermes_home/"memory"/"MEMORY.md"` (15+ occurrences)
- `load_dotenv()` mock added to config integration tests

### Round 4: Module Naming Staleness
- `*_tools` → `*_tool` across 8+ test files (clarify, memory, skills, process, etc.)
- `clarify()` parameter: `options=` → `choices=`
- `patch()` parameters: `old_str/new_str` → `old_string/new_string`

### Round 5: Outdated References
- `test_main_integration.py`: `build_model_caller` no longer exists
- `test_api` function removed → updated assertions

### Round 6: Final 2 Fixes (977 passed)
- `tests/cli/test_session_storage.py`: `"type"` → `"role"` (same Pattern 3, CLI subdir)
- `tests/test_e2e.py`: `search_files` dispatch missing `"target": "files"` (Pattern 9)

---

## Integration Test Report (Session: 2026-06-09)

**Method**: Real API (qwen3.6-plus via DashScope), PTY interaction with `python -m src.main`

### Coverage: 13/13 OpenSpec modules (100%), 50/50 tests passed

| Module | Tests | Pass |
|--------|-------|------|
| session-storage | 5 | 5 |
| tool-runtime | 12 | 12 |
| memory-system | 3 | 3 |
| provider-runtime | 4 | 4 |
| tool-search | 4 | 4 |
| conversation-loop | 8 | 8 |
| skill-system | 2 | 2 |
| context-compression | 2 | 2 |
| insights-metrics | 2 | 2 |
| unified-config-system | 3 | 3 |
| system-prompt-assembly | 4 | 4 |
| add-mcp-server-support | 1 | 1 |

### Tool Execution: 40+ calls, 100% success rate
Verified: terminal, read_file, write_file, patch, search_files, execute_code, clarify, todo, memory, search_tools

### Issues Found
1. **MEMORY.md deduplication**: `add_entry` appends without dedup — "User likes Python" repeated 6x
2. **pyproject.toml**: `better-sqlite3` (Node.js package, not Python) — removed
