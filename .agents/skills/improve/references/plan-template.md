# Plan NNN: <Imperative title - what will be true after this plan>
> **Executor instructions**: Follow this plan step by step. Run every verification command and confirm the expected result before moving to the next step. If anything in the "STOP conditions" section occurs, stop and report - do not improvise. When done, update the status row for this plan in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat <planned-at SHA>..HEAD -- <in-scope paths>`
> If any in-scope file changed since this plan was written, compare the "Current state" excerpts against the live code before proceeding.

## Status
- **Priority**: P1 | P2 | P3
- **Effort**: S | M | L
- **Risk**: LOW | MED | HIGH
- **Depends on**: none | plans/NNN-*.md
- **Category**: bug | security | perf | tests | tech-debt | migration | dx | docs | direction
- **Planned at**: commit `<short SHA>`, <YYYY-MM-DD>

## Context & Problem
<Clear context explaining why this change is needed, what issue it solves, and references to findings from the audit.>

## Scope of work
### In-scope
- Exact file paths and functions to modify or create.

### Out-of-scope
- Explicit boundaries: related files or components that must NOT be touched.

## Step-by-step implementation plan

### Step 1: <Short description of discrete change>
- **File**: `path/to/file.ext`
- **Current state**:
  ```lang
  // exact code snippet from file
  ```
- **Changes**:
  - Precise description of additions, modifications, or deletions.
- **Verify**: `<verification command>` -> <expected behavior>

## Test plan
- **New tests to write**: Specific cases to cover (happy path, edge cases, error conditions).
- **Reference exemplar**: Existing test pattern to emulate.

## Verification gates (Done criteria)
- [ ] Backend test suite: `.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"` -> 100% pass
- [ ] Frontend build: `npm run build` -> clean exit code 0
- [ ] Zero em-dash constraint: 0 em-dashes (`\u2014`) in Indonesian text and docs

## STOP conditions
- Stop implementation immediately and report back if:
  - An imported dependency or file structure differs unexpectedly from current state.
  - Verification fails with errors unrelated to the scoped changes.
  - A design decision or domain tradeoff is required.
