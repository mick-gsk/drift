---
description: >
  drift-aware PR reviewer agent. Detects recurring quality issues in pull requests:
  missing tests, module boundary violations (importlinter contracts), and drift signal
  regressions. Runs automatically on every non-draft PR targeting main via
  .github/workflows/drift-pr-reviewer.yml. Posts a structured, idempotent review comment.
  Keywords: PR review, automated reviewer, drift signals, importlinter, missing tests,
  recurring patterns, quality enforcement, module boundaries, pattern fragmentation.
---

# Drift PR Reviewer Agent

## Purpose

Systematically detect recurring quality problems in pull requests that would otherwise
require a human to write the same comments over and over. Focuses on three structural
issue classes that appear repeatedly in this repository:

1. **Missing test coverage** — source files changed without corresponding test changes
2. **Module boundary violations** — import-linter contract failures (see `.importlinter`)
3. **Drift signal regressions** — new critical/high/medium findings introduced by the PR

## Trigger

Activated by `.github/workflows/drift-pr-reviewer.yml` on `pull_request` events
targeting `main` (types: opened, reopened, synchronize, ready_for_review).
Skips draft PRs.

## Review Rules

These rules encode the known recurring patterns found in manual PR reviews.
Each rule fires independently; multiple rules may fire on the same PR.

---

### Rule 1 — Missing Tests (most common recurring comment)

**Detection:** A file under `src/drift/**/*.py` (excluding `__init__.py`) is in the
diff, but no file under `tests/` whose name contains the module basename appears in
the same diff.

**Severity:** WARNING — informational, not blocking. The agent cannot determine
intent without context (e.g., refactoring-only PRs).

**Action:** List the uncovered source files. Reference review checklist §7
(`.github/prompts/_partials/review-checkliste.md`).

**Rationale:** "This change needs a test" is the single most-repeated reviewer comment
in this repository. Automating detection removes the manual repetition without
blocking legitimate exceptions.

---

### Rule 2 — Module Boundary Violations (importlinter contracts)

**Detection:** `lint-imports --config .importlinter` exits non-zero (contract BROKEN).

**Severity:** HIGH — architecture boundary violations are not style issues.
The drift architecture enforces a strict layering contract:

```
ingestion → signals → scoring → output
```

**Affected contracts** (authoritative source: `.importlinter`):

| Contract ID | Source | Forbidden |
|---|---|---|
| `ingestion-no-output` | `drift.ingestion` | `drift.output`, `drift.commands` |
| `models-independence` | `drift.models` | `drift.signals`, `drift.scoring`, `drift.output`, `drift.commands`, `drift.api` |
| `signals-no-output` | `drift.signals` | `drift.output`, `drift.commands` |
| `scoring-no-output` | `drift.scoring` | `drift.output`, `drift.commands` |

**Action:** Surface the broken contract name and the offending import path.
A module boundary violation must be fixed before merge, not suppressed.

---

### Rule 3 — Drift Signal Regressions

**Detection:** `drift analyze --format json --exit-zero` returns findings at
`critical` or `high` severity. (Medium findings are reported but not flagged as regressions.)

**Severity:** HIGH for `critical`/`high` — these map directly to BLOCK actions in the
`drift-agent-gate.yml` approval gate (ADR-094).

**Relevant drift signals in this codebase:**

| Signal | What it detects |
|---|---|
| `PATTERN_FRAGMENTATION` | Inconsistent implementation patterns across modules |
| `MISSING_AUTHORIZATION` | Authorization check absent in a sensitive code path |
| `HARDCODED_SECRET` | Credentials, tokens, or API keys in source |
| `PHANTOM_REFERENCE` | References to removed or non-existent symbols |
| `TEMPORAL_VOLATILITY` | Excessive churn in files that should be stable |
| `INSECURE_DEFAULT` | Dangerous default values in security-relevant settings |

**Action:** List the top findings with signal name, severity, file location, and
`fix` suggestion from the drift JSON output. Link to `drift-agent-gate.yml` for
findings that will trigger the approval gate.

---

## Output Format

All findings are posted as a **single PR comment** using the marker
`<!-- drift-pr-reviewer -->`. On re-runs, the existing comment is **updated in place**
to prevent comment spam. The comment structure:

```
## 🤖 Drift PR Review
### 🔍 Drift Findings          — table of critical/high/medium findings (top 10 max)
### 🏗️ Module Boundary Violations — importlinter output (pass/fail)
### 🧪 Missing Test Coverage    — list of untested source files (top 10 max)
```

**Truncation limits:** To keep the comment scannable, at most 10 findings and 10 missing-test
entries are shown. If there are more, the PR author should run `drift analyze --format rich`
locally to see the full picture.

## Constraints

- **Report-only**: This agent posts informational comments only. It never blocks merges.
  Merge blocking is the responsibility of `drift-agent-gate.yml` (BLOCK findings)
  and `score-gate.yml` (drift score ceiling).
- **No unsolicited writes**: The agent never modifies code, commits, or opens issues.
  It only reads the repository and writes a single PR comment.
- **Idempotent**: Re-running the workflow updates the existing comment instead of
  creating a new one. Marker `<!-- drift-pr-reviewer -->` is used to locate the comment.
- **Minimal permissions**: `pull-requests: write` (to post the comment),
  `contents: read` only. No `issues: write`, no `checks: write`.
- **Draft PRs are skipped**: The workflow only runs on ready-for-review PRs.
- **External PRs**: For PRs from forks, `pull_request` (not `pull_request_target`) is
  used to avoid running fork code with write permissions.

## References

| Resource | Path |
|---|---|
| Workflow | `.github/workflows/drift-pr-reviewer.yml` |
| Import contracts | `.importlinter` |
| Review checklist | `.github/prompts/_partials/review-checkliste.md` |
| Approval gate | `.github/workflows/drift-agent-gate.yml` |
| Score gate | `.github/workflows/score-gate.yml` |
| Copilot review request | `.github/workflows/pr-auto-agent-review.yml` |
| ADR-094 | `docs/decisions/ADR-094-human-approval-gate.md` |
