---
name: simplify-and-harden
description: "Post-completion self-review for coding agents that runs simplify, harden, and micro-documentation passes on non-trivial code changes. Use when: a coding task just completed, the diff touches executable source files with 10+ changed lines or high-impact logic (auth, validation, queries, file paths, network, concurrency). Feeds recurring findings into self-improving-agent via .learnings/LEARNINGS.md."
argument-hint: "Run after completing a coding task. Provide the list of modified files if not auto-detected."
---

# Agent Skill: Simplify & Harden

Post-completion self-review: clean, harden, and document your work before moving on.

Source: https://clawhub.ai/pskoett/simplify-and-harden (v1.0.1, MIT-0, VirusTotal: Benign, OpenClaw: Benign HIGH CONFIDENCE)

## Trigger Conditions

Activate automatically when ALL of the following are true:

1. The agent has completed its primary coding task
2. The diff contains a **non-trivial** code change:
   - Touches at least one executable source file (`*.py`, `*.ts`, `*.js`, `*.go`, `*.rs`, etc.)
   - AND includes either ≥10 changed non-comment/non-whitespace lines OR at least one high-impact logic change (auth/authz, input validation, data access, external commands, file paths, network requests, concurrency)
3. The skill has not already run on this task (no re-entry loops)

**Does NOT activate** when:
- The change is docs-only, config-only, comments-only, formatting-only, generated artifacts only, or tests-only
- The agent failed or was interrupted
- User explicitly skips via `--no-review`

## Scope Constraints

**Hard rule: Only touch code modified in this task.**

- Do NOT refactor adjacent code that was not modified
- Do NOT introduce new dependencies or architectural changes
- Flag out-of-scope concerns in the summary output rather than acting on them

**Budget limits:**
- Maximum additional changes: **20% of the original diff size** (lines changed)
- Maximum execution time: **60 seconds**
- If either limit is hit, stop and output what you have with a `budget_exceeded` flag

## Pass 1: Simplify

**Objective:** Reduce unnecessary complexity introduced during implementation.

**Default posture:** Simplify, don't restructure. Bias heavily toward cosmetic fixes. Refactoring is the exception.

**Fresh-eyes start (mandatory):** Before any edits, re-read all code added or modified with fresh eyes. Actively look for obvious bugs, confusing logic, brittle assumptions, and naming issues.

### Review Checklist

- **Dead code** — debug logs, commented-out attempts, unused imports, temp variables
- **Naming clarity** — function/variable names that made sense mid-implementation but read poorly after
- **Control flow** — nested conditionals that can be flattened, deep nesting replaceable by early returns
- **API surface** — exposed more than necessary? Can public methods become private?
- **Over-abstraction** — classes or wrappers not justified by current scope
- **Consolidation** — logic spread across functions/files when it could live in one place

### Simplify Actions

- **Cosmetic fix** (dead code, unused imports, naming, control flow, visibility reduction) → applied automatically if within budget
- **Refactor** (consolidation, restructuring, abstraction changes) → proposed ONLY when genuinely necessary

**Refactor Stop Hook (mandatory):** Any refactor triggers an interactive prompt:

```
[simplify-and-harden] Refactor proposal (N of M):

  What: [description]
  Why: [rationale]
  Files affected: [list]
  Estimated diff: [+/- lines]

  [approve] [reject] [show diff] [skip all refactors]
```

Wait for explicit human approval before applying. Do not batch refactor proposals.

## Pass 2: Harden

**Objective:** Close security and resilience gaps while the agent still understands the code's intent.

Ask: *"If someone malicious saw this code, what would they try?"*

### Review Checklist

- **Input validation** — external inputs validated before use? Type coercion, bounds checks, unconstrained strings?
- **Error handling** — catch blocks specific? Errors logged without leaking sensitive data? Swallowed exceptions?
- **Injection vectors** — SQL injection, XSS, command injection, path traversal, template injection
- **Auth/authz** — new endpoints enforce auth? Permission checks present and correct? Privilege escalation risk?
- **Secrets** — hardcoded API keys, tokens, passwords? Connection strings parameterized? Credentials in logs?
- **Data exposure** — error output leaks internal state, stack traces, DB schemas, or PII?
- **Dependency risk** — new dependencies introduced? Well-maintained, properly versioned, no known CVEs?
- **Race conditions** — shared resources synchronized? TOCTOU vulnerabilities?

### Harden Actions

- **Patch** (adding validation, escaping output, removing hardcoded secret) → applied automatically if within budget
- **Security refactor** (restructuring auth flow, replacing vulnerable pattern) → ALWAYS requires human approval

Same Refactor Stop Hook applies with added severity and attack vector context.

## Pass 3: Document (Micro-pass)

**Objective:** Capture non-obvious decisions while the agent still remembers why it made them.

**Rules:**
- For logic requiring >5 seconds of "why does this exist?" thought: add a single-line comment
- For any workaround or hack: add a comment with context and a TODO with removal conditions
- For performance-sensitive choices: note why current approach was chosen over obvious alternative
- **Maximum: 5 comments added per task**

## Self-Improvement Integration

After each run, normalize recurring findings into `pattern_key`s and hand off to `self-improving-agent`:

```
learning_loop:
  target_skill: "self-improvement"
  log_file: ".learnings/LEARNINGS.md"
  candidates:
    - pattern_key: "simplify.dead_code"     # simplify.* or harden.*
      pass: "simplify"
      finding_type: "dead_code"
      severity: "low"
      source_file: "src/..."
      source_line: 12
      suggested_rule: "Remove dead code before finalizing a task."
```

**Promote to `.learnings/LEARNINGS.md`** when a pattern crosses the recurrence threshold:
- ≥3 occurrences across ≥2 distinct tasks in a 30-day window
- Then consider promotion to `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md`

## Output Schema

```yaml
simplify_and_harden:
  version: "0.1.0"
  task_id: "<original task ID>"
  execution:
    mode: "interactive"
    human_present: true
  scope:
    files_reviewed: [...]
    original_diff_lines: N
    additional_changes_lines: N
    budget_exceeded: false
  simplify:
    applied: [...]
    flagged: [...]
    cosmetic_applied: [...]
  harden:
    applied: [...]
    flagged_critical: [...]
    flagged_advisory: [...]
  document:
    comments_added: N
    locations: [...]
  learning_loop:
    candidates: [...]
  summary:
    simplify_applied: N
    harden_applied: N
    harden_flagged_critical: N
    comments_added: N
    budget_utilization: "X%"
    review_followup_required: true|false
```

Set `review_followup_required: true` when any unresolved finding remains (critical/advisory flags, skipped refactors) or `budget_exceeded: true`.

## Prompt-based Integration (GitHub Copilot)

After completing the task, run the Simplify & Harden review:

1. Review only the files you modified
2. **Simplify:** Your default action is cleanup — remove dead code, unused imports, fix naming, tighten control flow, reduce unnecessary public surface. Apply these directly. Refactoring is NOT the default. Only propose a refactor when the code is genuinely wrong or the improvement is substantial. If you propose one, describe it and ask for approval before applying.
3. **Harden:** Check for input validation gaps, injection vectors, auth issues, exposed secrets, and error handling problems. Apply simple patches directly. For security refactors that change structure, describe the issue with severity and ask for approval.
4. **Document:** Add up to 5 comments on non-obvious decisions.
5. Output a summary of what you changed, what you flagged, and what you left alone.

## Core Invariants

- Scope lock — only files modified in the current task
- Budget cap — 20% max additional diff
- Simplify-first posture — cleanup is the default, refactoring is the exception
- Refactor stop hook — structural changes always require human approval
- Three passes — simplify, harden, document (in that order)
- Structured output — summary of applied, approved, rejected, and flagged items
