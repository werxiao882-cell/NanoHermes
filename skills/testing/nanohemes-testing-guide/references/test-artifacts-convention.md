# Testing Artifacts Convention

## Directory Structure

```
testing-artifacts/
├── reports/    # Test reports (Markdown)
├── scripts/    # Helper scripts (Python/Bash)
└── logs/       # Test run logs
```

Create with: `mkdir -p testing-artifacts/{reports,scripts,logs}`

## Conflict Resolution Rules

1. **Never delete historical reports** — even if filename matches, never overwrite or delete existing reports
2. **Auto-rename on collision** — if `report-2026-06-09-2230.md` exists, use `report-2026-06-09-2230-2.md` (append sequence number)
3. **Script reuse first** — check `testing-artifacts/scripts/` for similar scripts before creating new ones; modify existing if functional overlap
4. **Log isolation by timestamp** — each test run gets a unique timestamp-named log file

## File Naming

- Reports: `report-YYYY-MM-DD-HHMM.md` or `report-YYYY-MM-DD-HHMM-N.md` (N = collision counter)
- Scripts: descriptive kebab-case, e.g., `check-session-storage.py`
- Logs: `test-YYYYMMDD-HHMM.log`

## Rationale

Test outputs are diagnostic artifacts. Historical reports enable comparison across runs and regression tracking. Overwriting destroys evidence.
