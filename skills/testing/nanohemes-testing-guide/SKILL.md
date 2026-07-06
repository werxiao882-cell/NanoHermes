---
name: nanohemes-testing-guide
description: "Use when testing NanoHermes AI Agent system — provides progressive-disclosure testing methodology with 131 test cases across 15 core modules, advanced scenarios, and report templates."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [testing, nanohemes, qa, e2e, progressive-disclosure]
    related_skills: [writing-plans, requesting-code-review]
---

# NanoHermes Testing Guide

## Overview

Complete end-to-end testing methodology for the NanoHermes AI Agent system, covering **15 core modules** with **131 test cases**, **36 advanced scenarios**, and reusable report templates. Designed for progressive disclosure — load only the detail you need.

**Target project**: `/mnt/d/code/NanoHermes` (Python self-evolving AI Agent, ~960 tests, 15 modules)

## When to Use

- Running functional verification on NanoHermes after code changes
- Onboarding new testers/QA to the NanoHermes codebase
- Preparing release validation or regression testing
- Diagnosing module-specific failures (load the relevant reference file)
- Setting up automated test pipelines

**Don't use for**: Unit-level pytest runs (use `python -m pytest tests/` directly), or testing unrelated Python projects.

## Quick Start — Core Test Flow

The testing process follows **10 sequential steps**, each validating a different system layer:

| Step | Focus | Key Commands | Expected |
|------|-------|-------------|----------|
| 1 | 启动验证 | `python -m src.main` | 配置加载、工具注册、记忆注入 |
| 2 | 基础对话 | 发送"你好" | 响应 <10 秒，流式输出正常 |
| 3 | 工具系统 | 测试 terminal/read_file/write_file/patch/search_files/execute_code/clarify | 12 个工具全部可用 |
| 4 | 会话存储 | 检查 `~/.nanohermes/sessions/` | JSONL 文件 + SQLite 元数据 |
| 5 | 记忆系统 | 检查 `~/.nanohermes/memory/` | MEMORY.md/USER.md 正确注入 |
| 6 | Provider 运行 | 观察 API 调用 | DashScope qwen3.6-plus 正常响应 |
| 7 | 对话循环 | 上下文保持、错误恢复、多工具调用 | 上下文理解准确，错误不崩溃 |
| 8 | 配置系统 | 验证优先级链：显式 > JSON > .env > 默认 | 配置正确加载 |
| 9 | TUI 界面 | 界面渲染、命令处理、键盘交互 | 流式输出、Tab 补全正常 |
| 10 | 边界情况 | 空输入、超长输入、特殊字符 | 优雅处理，无崩溃 |

**Environment setup** (run before testing):
```bash
cd /mnt/d/code/NanoHermes
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate py312
# Verify: .env has DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME
```

## Progressive Disclosure — How to Load Details

This skill uses **progressive disclosure** to avoid overwhelming context. Start with this SKILL.md, then load specific reference files as needed:

### Level 1: This file (always loaded)
- Trigger conditions, quick start, test flow overview
- Environment setup and verification checklist

### Level 2: Test case catalog (load when executing tests)
```
skill_view(name='nanohemes-testing-guide', file_path='references/test-cases.md')
```
→ **131 test cases** across 15 modules with checkable status boxes

### Level 3: Advanced scenarios (load for deep testing)
```
skill_view(name='nanohemes-testing-guide', file_path='references/advanced-scenarios.md')
```
→ **36 advanced scenarios**: tool combinations, session management, memory conflicts, error injection, performance benchmarks, security testing

### Level 4: Troubleshooting (load when things go wrong)
```
skill_view(name='nanohemes-testing-guide', file_path='references/troubleshooting.md')
```
→ Known issues, failure patterns, debug procedures, performance metrics

### Level 4b: PTY test results (load when planning PTY-based E2E tests)
```
skill_view(name='nanohemes-testing-guide', file_path='references/pty-test-results.md')
```
→ Real PTY test execution results: 23/23 pass, performance metrics, SQLite schema verified

### Level 4c: Test artifacts convention (load when organizing test outputs)
```
skill_view(name='nanohemes-testing-guide', file_path='references/test-artifacts-convention.md')
```
→ `testing-artifacts/` directory rules: never overwrite reports, auto-rename on collision, script reuse first

### Level 5: Report template (load when writing results)
```
skill_view(name='nanohemes-testing-guide', file_path='references/report-template.md')
```
→ Reusable markdown test report template. **Must save to** `testing-artifacts/reports/report-YYYY-MM-DD-HHMM.md` — never overwrite existing reports; auto-append sequence number on collision.

### Level 6: Debugging guides (load when diagnosing specific failures)
```
skill_view(name='nanohemes-testing-guide', file_path='references/sqlite-counter-fix.md')
```
→ SQLite counter debugging guide: how to diagnose and fix message_count/tool_call_count always being 0.

## Test Coverage Summary

| Module | Test Cases | Status |
|--------|-----------|--------|
| session-storage | 7 | ⬜ |
| tool-runtime | 12 | ⬜ |
| memory-system | 5 | ⬜ |
| provider-runtime | 6 | ⬜ |
| unified-config-system | 7 | ⬜ |
| system-prompt-assembly | 8 | ⬜ |
| tool-search | 6 | ⬜ |
| conversation-loop | 10 | ⬜ |
| multi-agent-delegation | 5 | ⬜ |
| skill-system | 6 | ⬜ |
| context-compression | 5 | ⬜ |
| insights-metrics | 4 | ⬜ |
| add-mcp-server-support | 6 | ⬜ |
| cli (TUI) | 8 | ⬜ |
| auxiliary | 4 | ⬜ |
| **Advanced scenarios** | **36** | ⬜ |
| **TOTAL** | **167** | ⬜ |

## Key Paths

| Resource | Path |
|----------|------|
| Project root | `/mnt/d/code/NanoHermes` |
| Session storage | `~/.nanohermes/sessions/` (JSONL) |
| Session metadata | `~/.nanohermes/sessions.db` (SQLite) |
| Memory files | `~/.nanohermes/memory/MEMORY.md`, `USER.md` |
| MCP config | `~/.nanohermes/mcp_servers.json` |
| Environment | `.env` (DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, MODEL_NAME) |
| **Test outputs** | `testing-artifacts/{reports,scripts,logs}` (all test artifacts go here) |
| Test guide doc | `TESTING_GUIDE.md` (project root, full 131-case guide) |

## Common Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run module tests
python -m pytest tests/tools/ -v
python -m pytest tests/provider/ -v

# E2E test (interactive)
python -m src.main              # normal mode
python -m src.main --debug      # debug mode (full JSON request/response)
python -m src.main --resume     # resume last session

# Clean test data
rm -rf ~/.nanohermes/sessions/*
rm -f ~/.nanohermes/sessions.db
rm -rf ~/.nanohermes/memory/*

# Verify storage
ls -la ~/.nanohermes/sessions/
sqlite3 ~/.nanohermes/sessions.db "SELECT COUNT(*) FROM sessions;"
cat ~/.nanohermes/memory/MEMORY.md
```

## Common Pitfalls

1. **MEMORY.md duplicate entries** — AI repeatedly writes same info without dedup. Impact: low (redundancy). Fix: add dedup mechanism before calling `memory` tool.
2. **search_files over-searching** — AI calls search_files 7+ times instead of using known `/tools` command. Impact: low (efficiency). Fix: narrow intent in prompt.
3. **API cost during testing** — real API calls cost money. Control test rounds and monitor token usage via status bar.
4. **Rate limiting** — rapid consecutive requests may trigger 429. Space out requests or use `--debug` mode to slow down.
5. **Stale test data** — old sessions interfere with new tests. Clean `~/.nanohermes/sessions/` before each test run.
6. **Skill not visible in current session** — newly created skills are cached at session start. Verify in a new session.
7. **Test artifacts scattered** — reports, scripts, and logs must go under `testing-artifacts/` (created by `mkdir -p testing-artifacts/{reports,scripts,logs}`). Never leave test output in project root. See `references/test-artifacts-convention.md` for conflict resolution rules.
8. **ConversationLoop max_iterations hardcoded** — default 90, set in `src/conversation/loop.py` constructor. TUI (`src/cli/tui.py`) creates ConversationLoop without passing `max_iterations`, so it always uses 90. No config-level override exists. If you need more iterations for complex tool-chain tests, either patch the TUI to pass it, or modify the default in `loop.py`.
9. **PTY TUI limitations** — prompt_toolkit's full visual rendering (status bar, tool panel) produces ANSI escape codes in PTY output that need stripping for clean text. CPR (cursor position request) warning is non-blocking and can be ignored. Use `process(action='poll')` to get output, allow 3-15s sleep between submits for LLM response.
10. **SQLite counters were zero** — `message_count` / `tool_call_count` in `sessions` table were never incremented. **Fixed**: `session_db.py:insert_message` auto-calls `increment_message_count` for user/assistant/system roles; `event_handler.py:_on_tool_start` calls `increment_tool_call_count`. If you find counters at 0 again, check these two call sites.
11. **TUIApp dependency injection** — TUIApp `__init__` accepts `session_db`, `jsonl_store`, `memory_manager`, `skill_manager` keyword args using `_UNSET` sentinel pattern. `_UNSET` = auto-initialize, `None` = disabled, instance = use injected. Tests that mock storage must pass these as kwargs: `TUIApp(session_db=my_db, jsonl_store=my_store)`.
12. **test_integration.py import failure** — `tests/tools/test_integration.py` imports `src.tools.toolsets` which doesn't exist. Skip with `--ignore=tests/tools/test_integration.py` until the module is created or the test is updated.
13. **Error auto-recovery during PTY testing** — When PTY tests hit errors (startup crash, missing dependency, config error), don't stop. Follow the repair cycle: detect → analyze → fix (clear cache / install package / fix config / retry) → verify → continue from failure point. Max 3 retry attempts per error. Log repairs to `testing-artifacts/logs/fix-log.md`.

## Verification Checklist

After running tests:
- [ ] All 15 core modules tested (load `references/test-cases.md` for checklist)
- [ ] Advanced scenarios covered (load `references/advanced-scenarios.md`)
- [ ] No unhandled crashes or exceptions
- [ ] Session storage contains valid JSONL + SQLite data
- [ ] Memory files persist across restarts
- [ ] Test report generated (load `references/report-template.md`)
- [ ] Known issues documented in report
