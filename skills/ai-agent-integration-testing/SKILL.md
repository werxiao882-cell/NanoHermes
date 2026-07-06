---
name: ai-agent-integration-testing
description: "Integration testing for AI Agent CLI systems — PTY-driven conversation simulation, tool chain verification, OpenSpec-driven test design, and real-API validation."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ai-agent, integration-testing, pty, conversation, tool-verification, openspec]
    related_skills: [python-test-maintenance, capability-gap-analysis]
---

# AI Agent Integration Testing

## Overview

Methodology for testing AI Agent CLI systems (like NanoHermes, Claude Code, etc.) by starting the agent in PTY mode, simulating real user conversations, and verifying tool chains, memory persistence, session storage, and multi-turn context — all with **real API requests** (no mocks).

**When to use:**
- User asks to "test if this AI agent works"
- Need to verify an agent's tool system, memory, session storage, or conversation loop
- Want to test against a specification (e.g., OpenSpec) with real LLM interactions
- Unit tests pass but you need end-to-end validation

**Don't use for:**
- Unit test debugging (use `python-test-maintenance`)
- Capability gap analysis (use `capability-gap-analysis`)
- Mock-based API testing (use standard pytest patterns)

## Core Methodology

### Step 1: Environment Setup

```bash
conda create -y -n py312 python=3.12 && conda activate py312
cd /path/to/project && pip install -e ".[dev]"
# Verify API credentials
cat .env
```

### Step 2: Start Agent in PTY Mode

Use `terminal(pty=True, background=True)` or spawn a PTY subprocess. Wait for the TUI to render before sending input.

### Step 3: Design Test Cases from OpenSpec

Map each completed OpenSpec to test cases:
```bash
for dir in openspec/changes/*/; do
  name=$(basename "$dir")
  if [ -f "$dir/tasks.md" ]; then
    total=$(grep -cE "\[ [xX]\]" "$dir/tasks.md" 2>/dev/null || echo 0)
    done=$(grep -c "\[x\]" "$dir/tasks.md" 2>/dev/null || echo 0)
    [ "$done" = "$total" ] && [ "$total" -gt 0 ] && echo "$name: $done/$total"
  fi
done
```

For each completed spec, design test cases covering: core functionality, edge cases, and integration with other features.

**Expanding test coverage**: When the user asks for more test cases, analyze the project's architecture docs (README.md, AGENTS.md, OpenSpec specs) to extract all modules and constraints. Each module maps to 4-12 test cases across functional, integration, boundary, error, performance, and security dimensions. See `references/nanohermes-testing-reference.md` for a complete methodology and a 131-case example from the NanoHermes project.

### Step 4: Execute Test Scenarios

| Test Type | Example Input | Verify |
|-----------|--------------|--------|
| Basic conversation | "Hello, introduce yourself" | AI responds correctly |
| Tool: read | "Read pyproject.toml" | read_file called, content shown |
| Tool: write | "Create /tmp/test.txt with X" | write_file called, file exists |
| Tool: edit | "Change line 2 to Y" | patch called, file updated |
| Tool: search | "Find all .py files" | search_files called, results correct |
| Tool: execute | "Calculate primes under 100" | execute_code called, result correct |
| Multi-turn context | "What was the file I just created?" | AI references prior turns |
| Error handling | "Read /tmp/not_exist.txt" | Graceful error message |
| Memory | "Remember I prefer Python" | MEMORY.md updated |
| TUI commands | /tools, /sessions, /skills | Correct output |

### Step 5: Verify Persistence

```bash
ls ~/.nanohermes/sessions/*.jsonl
sqlite3 ~/.nanohermes/sessions.db "SELECT count(*) FROM sessions;"
cat ~/.nanohermes/memory/MEMORY.md
cat ~/.nanohermes/memory/USER.md
```

### Step 6: Document Results

Record test execution in markdown as you go:
```markdown
## Test: [ID] [Description]
**User input**: "..."
**AI behavior**: Called [tool], result: ...
**Result**: Pass / Fail
```

## PTY Interaction Pattern

```
terminal(pty=True, background=True, command="cd /path && python -m src.main")
process(action='wait', session_id='...', timeout=20)     # Wait for startup
process(action='submit', session_id='...', data="Hello") # Send message
process(action='wait', session_id='...', timeout=60)     # Wait for response
# ... repeat for each test ...
process(action='submit', session_id='...', data="/quit") # Clean exit
```

**Important**: Use 60-120s timeouts for LLM responses. Shorter timeouts return partial output.

## Pitfalls

1. **Assuming API signatures**: Always `inspect.signature()` before writing test code. Parameters may differ from expectations.

2. **Mock vs Real API**: For integration testing, use real API. Mock-based tests miss tool-chain integration bugs.

3. **PTY buffering**: Use `process(action='log')` after completion to see full output.

4. **Memory deduplication**: `add_entry` appends without checking duplicates. Expect repeated entries in MEMORY.md for frequently mentioned facts. Known limitation, not a test failure.

5. **AI over-searching**: When asked to "test tools", AI may call search_files multiple times with different patterns instead of using /tools. Expected behavior — AI interprets requests literally.

6. **Cleanup**: Always send `/quit` before killing the process.

## Verification Checklist

- [ ] Environment set up (conda, deps, API keys)
- [ ] Agent starts in PTY mode
- [ ] Basic conversation works
- [ ] Each tool type tested (read/write/edit/search/execute)
- [ ] Multi-turn context verified
- [ ] Error handling tested
- [ ] Memory persistence verified
- [ ] Session storage verified (SQLite + JSONL)
- [ ] TUI commands tested
- [ ] Agent exits cleanly
- [ ] Results documented
