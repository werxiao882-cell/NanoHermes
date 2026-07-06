---
name: capability-gap-analysis
description: "Use when comparing a reference implementation against a target codebase to identify missing capabilities, then creating structured OpenSpec proposals to close the gaps."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [analysis, openspec, architecture, capability-mapping, gap-analysis]
    related_skills: [writing-plans, hermes-agent-skill-authoring, ai-agent-integration-testing]
---

# Capability Gap Analysis

## Overview

Systematic methodology for comparing a reference implementation (e.g., Claude Code, an industry-standard system) against a target codebase to identify truly missing capabilities, then creating structured OpenSpec proposals to close each gap.

The core challenge: not everything the reference has is worth implementing, and not everything the target "lacks" is actually missing — it may be implemented differently or covered by an existing spec. This skill provides a rigorous triple-filter methodology to find only the gaps that matter.

## When to Use

- User asks to compare two systems and find what's missing
- Analyzing a competitor/reference codebase for feature gaps
- Creating OpenSpec proposals to extend an existing project
- Evaluating whether a planned feature already exists in a different form
- Deep architectural analysis of a reference system's DFX (Design for Excellence) patterns

## Don't Use For

- Simple feature checklist comparisons (use `writing-plans` instead)
- Debugging why something doesn't work (use `systematic-debugging`)
- Writing implementation plans for known features (use `writing-plans`)

## Triple-Filter Methodology

To find **truly missing** capabilities, apply three filters in sequence:

### Filter 1: Reference Has It

Identify the capability in the reference implementation:
- Read source code for the specific mechanism
- Document the file, line count, and key design decisions
- Understand the DFX patterns (error handling, retry, concurrency, etc.)

### Filter 2: Existing Specs Don't Cover It

Cross-reference against the target's existing OpenSpec proposals:
```bash
# List all active (non-archived) OpenSpec changes
ls openspec/changes/ | grep -v archive

# Read each proposal to understand scope
for dir in openspec/changes/*/; do
  echo "=== $(basename $dir) ==="
  head -20 "$dir/proposal.md"
done

# Check tasks.md for implementation status
grep -c "\[ \]" openspec/changes/*/tasks.md
```

If an existing spec covers the capability (even partially), it's **not a gap** — it's either already planned or in progress.

### Filter 3: Source Code Doesn't Implement It

Scan the actual source code to verify implementation status:
```python
import os, re

# Define patterns that would indicate the capability exists
patterns = ["error_handler", "retry", "timeout", "concurrent", ...]

# Scan all source files
for root, dirs, files in os.walk("src/"):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path) as fh:
                content = fh.read()
            for p in patterns:
                if re.search(p, content, re.IGNORECASE):
                    print(f"Found '{p}' in {path}")
```

If the source code implements the capability (even with a different name or approach), it's **not a gap**.

### Result: Truly Missing = Reference Has ∧ Specs Don't ∧ Source Doesn't

Only capabilities that pass all three filters warrant new OpenSpec proposals.

## OpenSpec Proposal Structure

Each capability gap gets its own OpenSpec change with this structure:

```
openspec/changes/<change-name>/
├── proposal.md          # Why + What changes + Impact
├── design.md            # Detailed design decisions, trade-offs
├── tasks.md             # Numbered implementation tasks with checkboxes
└── specs/
    └── <spec-name>/
        └── spec.md      # Gherkin-style requirements with scenarios
```

### proposal.md Template

```markdown
# Proposal: <Title>

## Why

<Context: what exists in the reference, what's missing in the target, why it matters>

## What Changes

- <Bullet list of concrete changes>

## Impact

- **New specs**: N specs added to <existing-or-new-change>
- **Modified specs**: N specs updated
- **Existing code**: <what changes, what stays the same>
```

### design.md Template

```markdown
# Design: <Title>

## Analysis Scope

<What was compared, which files, which versions>

## Reference Implementation

<How the reference does it — code excerpts, file paths, line counts>

## Target Current State

<What the target currently has — verified by source scan>

## Design Decisions

<Why choose approach A over B, trade-offs, integration points>
```

### spec.md Template (Gherkin-style)

```markdown
## ADDED Requirements

### Requirement: <Requirement name>

System SHALL <behavior>.

#### Scenario: <Scenario name>

- **WHEN** <trigger condition>
- **THEN** <expected outcome>
- **AND** <additional expectation>
```

### tasks.md Template

```markdown
# Tasks: <Title>

## 1. <Subsystem name>

- [ ] 1.1 <Specific task>
- [ ] 1.2 <Specific task>
- [ ] 1.3 <Specific task>
```

## DFX Analysis Patterns

When analyzing a reference implementation's DFX (Design for Excellence), look for these patterns:

| DFX Dimension | What to Look For | Example |
|---------------|------------------|---------|
| Error Handling | Error classification, retry logic, fallback chains | `withRetry.ts` (822 lines) |
| Concurrency | Partitioning, limits, semaphores, backpressure | `partitionToolCalls()` |
| Resource Management | Budgets, quotas, truncation, timeouts | `applyToolResultBudget()` |
| State Management | Context modifiers, state machines, transitions | `ContextModifier` |
| Observability | Logging, metrics, tracing, debugging hooks | `dump-prompts`, `/context` |
| Security | Permission systems, sandboxing, input sanitization | Unicode steganography defense |

## Workflow

### Step 1: Deep Reference Analysis

Read the reference implementation thoroughly:
- Identify key files and their responsibilities
- Note line counts and complexity (signals importance)
- Document design patterns and DFX mechanisms
- Create a structured feature report

### Step 2: Map Existing Specs

```bash
# Get all active changes
changes=$(ls openspec/changes/ | grep -v archive)

# For each change, read proposal and check tasks
for name in $changes; do
  done=$(grep -c "\[x\]" "openspec/changes/$name/tasks.md" 2>/dev/null || echo 0)
  total=$(grep -cE "\[ [xX]\]" "openspec/changes/$name/tasks.md" 2>/dev/null || echo 0)
  echo "$name: $done/$total"
done
```

### Step 3: Source Code Verification

Use regex scans across the source tree to verify implementation status. Be thorough — capabilities may exist under different names.

### Step 4: Apply Triple Filter

Build a comparison table:

| Capability | Reference | Existing Spec | Source | Gap? |
|------------|-----------|---------------|--------|------|
| Feature A  | ✅ Yes    | ✅ Covered    | ✅ Impl | ❌ No |
| Feature B  | ✅ Yes    | ❌ Not in spec | ❌ Not impl | ✅ **Yes** |
| Feature C  | ✅ Yes    | ⚠️ Partial    | ❌ Not impl | ⚠️ Partial |

### Step 5: Create OpenSpec Proposals

For each confirmed gap:
1. Create the change directory structure
2. Write proposal.md (why + what + impact)
3. Write design.md (analysis + decisions)
4. Write spec.md files (Gherkin scenarios)
5. Write tasks.md (numbered checkboxes)

## Common Pitfalls

1. **False gaps**: The capability exists but under a different name. Always verify with source code scan before declaring a gap.

2. **Overlapping specs**: A capability may be partially covered by an existing spec. In this case, extend the existing spec rather than creating a duplicate.

3. **Ignoring implementation status**: An OpenSpec proposal doesn't mean the feature exists. Check `tasks.md` for `[x]` vs `[ ]` counts.

4. **Shallow reference analysis**: Don't just read documentation — read the actual source code. The real design decisions are in the code, not the docs.

5. **Missing DFX patterns**: Error handling, retry, concurrency limits, and resource budgets are often the most valuable capabilities to port, even if the core feature exists.

## Verification Checklist

- [ ] Reference implementation analyzed at source code level (not just docs)
- [ ] All existing OpenSpec changes reviewed for overlap
- [ ] Source code scanned with relevant patterns
- [ ] Triple filter applied: Reference has ∧ Specs don't ∧ Source doesn't
- [ ] Each gap has proposal.md, design.md, spec.md, and tasks.md
- [ ] Specs use Gherkin-style scenarios (WHEN/THEN/AND)
- [ ] Tasks are numbered, specific, and have checkbox format
- [ ] Design decisions documented with trade-offs

## Linked Files

- `references/claude-code-dfx-analysis.md` — Claude Code 2.1.69 DFX analysis (withRetry.ts 822 lines, toolOrchestration.ts 188 lines)
- `references/tool-dfx-gap-analysis.md` — Tool DFX gap analysis: retry, concurrency, context modifier, result budget, execution tracking. Includes OpenSpec file inventory and pseudo-code line counts.
