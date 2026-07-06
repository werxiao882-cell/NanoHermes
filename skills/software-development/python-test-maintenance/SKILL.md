---
name: python-test-maintenance
description: "Python test suite maintenance: pytest collection errors, mock env var conflicts, path drift, and encoding corruption."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [python, pytest, testing, maintenance, troubleshooting]
    related_skills: [systematic-debugging, test-driven-development, ai-agent-integration-testing]
---

# Python Test Suite Maintenance

## Overview

Common failure patterns when maintaining Python/pytest test suites, and how to fix them quickly. These are **not** bugs in the application code — they're test infrastructure issues that prevent tests from running at all.

**When to use:** pytest collection errors, import failures in tests, env var mocking issues, tests referencing wrong paths after implementation changes, syntax errors from corrupted files.

## Pattern 1: pytest Module Name Collision

**Symptom:**
```
import file mismatch:
imported module 'test_engine' has this __file__ attribute:
  /path/to/tests/compression/test_engine.py
which is not the same as the test file we want to collect:
  /path/to/tests/insights/test_engine.py
HINT: remove __pycache__ / .pyc files and/or use a unique basename
```

**Root cause:** Two test files in different directories share the same basename (e.g., `test_engine.py` in both `tests/compression/` and `tests/insights/`). pytest imports them as the same module name.

**Fix:** Rename one of the files with a unique prefix:
```bash
mv tests/compression/test_engine.py tests/compression/test_context_engine.py
mv tests/mcp/test_client.py tests/mcp/test_mcp_client.py
mv tests/mcp/test_registry.py tests/mcp/test_mcp_registry.py
mv tests/provider/test_integration.py tests/provider/test_provider_integration.py
```

**Prevention:** Use scoped prefixes for test files that might exist in multiple modules: `test_mcp_client.py`, `test_provider_integration.py`, `test_context_engine.py`.

## Pattern 2: `load_dotenv()` Overrides `mock.patch.dict(os.environ)`

**Symptom:** Test sets `mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True)` but the code still reads a different key (e.g., `DASHSCOPE_API_KEY`) from the real `.env` file.

**Root cause:** `load_dotenv()` is called inside `load_config()` and reads the real `.env` file, overwriting the mocked environment variables.

**Fix:** Mock `load_dotenv` in addition to mocking `os.environ`:
```python
with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
    with mock.patch("src.config.loader.load_dotenv"):
        config = load_config(provider="openai")
        # Now env is clean and load_dotenv won't pollute it
```

**Key insight:** Any code path that calls `load_dotenv()` will overwrite `mock.patch.dict(os.environ)` mocks. Always mock `load_dotenv` when testing environment-dependent behavior.

## Pattern 3: Test File Path Drift

**Symptom:** Tests fail with `FileNotFoundError` or assert failures because they reference wrong file paths.

**Root cause:** Implementation changed the storage location (e.g., files moved from `hermes_home/X.md` to `hermes_home/memory/X.md`) but tests weren't updated.

**Fix:** Search for the actual path construction in the source:
```python
# In file_provider.py:
self._memory_path = self._memory_dir / "MEMORY.md"  # _memory_dir = hermes_home / "memory"
```

Then update all test assertions to match:
```python
# Wrong (old):
memory_path = hermes_home / "MEMORY.md"

# Correct (new):
memory_path = hermes_home / "memory" / "MEMORY.md"
```

**Systematic approach:** When tests reference file paths, trace the path construction in the source implementation. Don't assume the test's path matches the implementation's path — they drift independently.

## Pattern 4: Unicode/Encoding Corruption

**Symptom:** `SyntaxError: unterminated string literal` in a test file that looks fine visually.

**Root cause:** File was saved with wrong encoding or got corrupted, replacing Chinese characters (or other multi-byte chars) with replacement characters (``).

**Fix:**
```bash
# Find corrupted characters
grep -Pn '\xEF\xBF\xBD' tests/test_file.py

# Or search for replacement character
grep -n '' tests/test_file.py
```

Then fix the corrupted strings. The replacement character `` (U+FFFD) indicates bytes that couldn't be decoded.

## Pattern 5: Field Name Mismatch Between Test and Implementation

**Symptom:** `KeyError: 'type'` when test accesses `messages[0]["type"]` but implementation stores `"role"`.

**Root cause:** Implementation uses different field names than what tests expect.

**Fix:** Check the actual record structure in the implementation:
```python
# In jsonl_store.py:
record = {"role": role, "timestamp": time.time()}  # Uses "role", not "type"
```

Update test to match:
```python
assert messages[0]["role"] == "user"  # Not "type"
```

## Pattern 6: Module Import Staleness (Plural vs Singular Naming)

**Symptom:**
```
ImportError: cannot import name 'clarify_tools' from 'src.tools'
ImportError: cannot import name 'memory_tools' from 'src.tools'
AttributeError: module 'src.tools' has no attribute 'skills_tools'
```

**Root cause:** Source modules were renamed from plural (`*_tools`) to singular (`*_tool`) — e.g., `clarify_tools.py` → `clarify_tool.py`, `memory_tools.py` → `memory_tool.py` — but tests still import the old names. This affects BOTH the `from src.tools import X` line AND the `importlib.reload(X)` line.

**Fix:** Bulk-rename all occurrences in test files:
```bash
# First verify what needs changing
grep -rn 'from src.tools import.*_tools\b' tests/tools/ | grep -v '_tool\b'

# Then bulk fix (covers all common patterns)
sed -i 's/clarify_tools/clarify_tool/g; s/memory_tools/memory_tool/g; \
s/skills_tools/skills_tool/g; s/process_tools/process_tool/g; \
s/cronjob_tools/cronjob_tool/g; s/delegation_tools/delegation_tool/g; \
s/code_execution_tools/code_execution_tool/g; \
s/search_tools/search_tool/g; s/session_search_tools/session_search_tool/g; \
s/file_tools/file_tool/g' tests/tools/*.py
```

**Also check:** `importlib.reload()` calls use the same variable names — both the import and reload must be updated together.

## Pattern 7: Parameter Name Mismatches

**Symptom:** `KeyError: 'options'` when calling `clarify(question="...", options=["A", "B"])` or `KeyError: 'status'` when calling `patch(path=..., old_str=...)`.

**Root cause:** Function signature uses different parameter names than what tests pass:
- `clarify()` uses `choices=` not `options=`
- `patch()` uses `old_string=` / `new_string=` not `old_str=` / `new_str=`

**Fix:** Search for the actual function signature in source, then update test calls:
```bash
# Find the function definition
grep -n 'def clarify(' src/tools/clarify_tool.py
# → def clarify(question, choices, ...)

# Update test calls
sed -i 's/options=/choices=/g' tests/tools/test_clarify.py
sed -i 's/old_str/old_string/g; s/new_str/new_string/g' tests/tools/test_default_tools.py
```

## Pattern 8: Outdated Function References

**Symptom:**
```
AssertionError: assert False where False = hasattr(main, 'test_api')
ImportError: cannot import name 'build_model_caller' from 'src.main'
```

**Root cause:** Tests reference functions that were refactored away or never existed in the current implementation. This is common when tests were written for a different architecture.

**Fix:** Read the current source to find what actually exists, then update tests:
```python
# Instead of testing for removed functions:
def test_import_main(self):
    from src import main
    assert hasattr(main, "main")
    assert hasattr(main, "main_chat")          # What actually exists
    assert hasattr(main, "list_sessions_command")  # What actually exists
```

**Rule:** Don't assume the test's expected functions exist. Verify against the current source.

## Pattern 10: API Signature Mismatch in Test Scripts

**Symptom:** `TypeError: build_client() missing 1 required positional argument: 'credentials'` or `TypeError: PromptAssembler.assemble() got an unexpected keyword argument 'messages'` — test script fails because it assumed a function signature that doesn't match the actual implementation.

**Root cause:** Writing test scripts or integration tests based on assumed API signatures rather than inspecting the actual code. This is especially common when the target project has evolved and the test author is working from memory or outdated documentation.

**Fix:** Always inspect the actual function signature before writing test code:
```python
import inspect, sys
sys.path.insert(0, "/path/to/project")

from src.provider.client_factory import build_client
print(inspect.signature(build_client))
# → (api_mode: 'ApiMode', credentials: 'CredentialResult') -> 'OpenAI | Anthropic'

from src.prompt.assembler import PromptAssembler
pa = PromptAssembler()
print(inspect.signature(pa.assemble))
# → () -> 'str'  (no parameters — uses set_* methods to set state)
```

**Rule:** Never assume function signatures match your expectations. Always `inspect.signature()` or `inspect.getsource()` the actual implementation before writing test code that calls it. This applies to:
- Constructor `__init__` signatures
- Method parameters
- Dataclass/data model fields (`dataclasses.fields()`)
- Module-level exports (`[x for x in dir(module) if not x.startswith('_')]`)

## Pattern 9: Tool Default Behavior Mismatch

**Symptom:** `assert data["total_found"] >= 1` fails with `0 >= 1` — the tool returned empty results even though the file clearly exists.

**Root cause:** The tool has a default mode that doesn't match what the test expects. Example: `search_files(pattern="*.txt")` defaults to `target="content"` (search inside file contents), but the test expects file-by-name matching (`target="files"`).

**Fix:** Make the test explicit about the intended mode:
```python
# Wrong — relies on default (content search):
dispatch("search_files", {"path": tmpdir, "pattern": "*.txt"})

# Correct — explicit target:
dispatch("search_files", {"path": tmpdir, "pattern": "*.txt", "target": "files"})
```

**Rule:** When dispatching tools with mode/strategy parameters, always specify the parameter explicitly in tests. Don't rely on defaults — if the default changes, the test silently passes with wrong semantics or fails confusingly.

## Quick Diagnostic Flow

When pytest fails to collect or run tests:

1. **Collection errors?** → Module name collisions (Pattern 1)
2. **Import errors — module not found?** → Missing dependencies
3. **Import errors — name not found?** → Module import staleness (Pattern 6) or wrong import path
4. **Env vars wrong?** → `load_dotenv()` override (Pattern 2)
5. **File not found?** → Path drift (Pattern 3)
6. **Syntax errors?** → Encoding corruption (Pattern 4)
7. **KeyError/assertion — wrong field?** → Field name mismatch (Pattern 5)
8. **KeyError/assertion — wrong param?** → Parameter name mismatch (Pattern 7)
9. **AttributeError/ImportError — function missing?** → Outdated references (Pattern 8)
10. **Empty results / 0 found when data exists?** → Tool default behavior mismatch (Pattern 9)

## Iterative Fix Workflow

When facing 20+ failures:

```bash
# 1. Quick overview — just counts, no tracebacks
pytest tests/ --tb=no -q | tail -5

# 2. Fix one category (e.g., all module name issues)

# 3. Quick verify — fast iteration
pytest tests/ --tb=no -q | tail -5

# 4. Repeat for each category

# 5. Final full verification
pytest tests/ -v --tb=short
```

**Key insight:** `--tb=no -q` gives near-instant feedback. Full tracebacks are only needed for the final verification or when investigating individual failures.

## References

- `references/nanohermes-test-fixes.md` — Concrete fix log from NanoHermes test suite (8 categories of failures fixed)

## Pitfalls

- **Don't just run `rm -rf __pycache__`** — this masks module name collisions. Renaming files is the real fix.
- **`mock.patch.dict(os.environ, clear=True)` is not enough** when code calls `load_dotenv()`. Always mock `load_dotenv` too.
- **Don't assume test paths match implementation paths** — trace the actual path construction in source.
- **Large test suites with `tail -N` pipe buffering** — output won't appear until the process finishes. Use `-q` flag for real-time progress, or check `process(action='log')` for completed output.
