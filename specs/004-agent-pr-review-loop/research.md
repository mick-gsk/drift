# Research: Agent PR Review Loop

**Phase 0 Output** | **Date**: 2026-04-30 | **Plan**: [plan.md](plan.md)

## Decision Log

### 1. Library structure: `src/drift/pr_loop/` vertical slice

**Decision**: Core logic lives in `src/drift/pr_loop/` as a Constitution-compliant library. `scripts/pr_review_loop.py` is a thin entry-point wrapper. `.github/skills/drift-pr-review-loop/SKILL.md` is the Copilot orchestration layer.

**Rationale**: Constitution Principle I (Library-First) requires all feature logic in `src/drift/`. The script approach alone would violate this and make the engine untestable in isolation. The SKILL is an agent primitive, not application logic — it sits outside `src/drift/` by design.

**Alternatives considered**: Pure `scripts/` shell script — rejected because (a) Windows-incompatible bash, (b) no unit-testable surface, (c) violates Constitution Principle I and II.

---

### 2. GitHub API: requesting `github-copilot[bot]` as a reviewer

**Decision**: Use `gh api --method POST /repos/{owner}/{repo}/pulls/{pr}/requested_reviewers --input -` with body `{"team_reviewers": [], "reviewers": []}` for users, or the `gh pr edit --add-reviewer github-copilot[bot]` shorthand.

**Rationale**: The Copilot code review bot is triggered by adding it as a reviewer via the standard GitHub Reviewers API. The reviewer slug is `github-copilot[bot]` for the app; however, the REST endpoint for requesting reviewers only accepts usernames or team slugs — app-based reviewers cannot be added via the standard `/requested_reviewers` endpoint. The correct trigger is: post a PR Review Request via the **Copilot-specific** mechanism — in practice, the bot monitors new PRs automatically if "Copilot code review" is enabled at repo level. The script's job is to detect the bot's review response, not necessarily to explicitly trigger it.

**Revised approach**: For repos where Copilot code review is enabled, the bot reviews automatically. The script polls `gh pr view <PR> --json reviews` until it sees a review from `github-copilot[bot]` or the timeout elapses.

**Alternatives considered**: `@github-copilot review` comment mention — undocumented, unreliable in automation.

---

### 3. Polling `gh pr view --json reviews` output schema

**Decision**: Use `gh pr view <PR-NUMBER> --json reviews,reviewDecision,statusCheckRollup` to collect the full review state in one call.

**Rationale**: The `reviews` field returns an array of `{author: {login}, state, body, submittedAt}`. States are `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED`. `reviewDecision` gives the aggregate verdict. This is sufficient to detect per-reviewer verdicts and new unresolved comments.

**Key field**: `author.login` will be `"github-copilot[bot]"` for Copilot reviews. The script compares `author.login` against the configured reviewer list.

**Alternatives considered**: GitHub REST API directly — feasible but `gh` CLI is already installed and auth-managed in this repo.

---

### 4. `drift.yaml` schema contract-test impact

**Decision**: After adding `pr_loop: PrLoopConfig | None` to `DriftConfig`, `drift.schema.json` must be regenerated via `python -c "from src.drift.config._loader import build_config_json_schema; ..."` (or the existing `make schema` target if present).

**Rationale**: `tests/test_config_schema.py` byte-compares the committed `drift.schema.json` against the live schema. Any `DriftConfig` field addition without schema regen causes CI failure.

**Action required in implementation**: Run schema regeneration as part of the implementation task, before committing.

---

### 5. Existing `drift-pr-review` skill: scope disambiguation

**Decision**: The new skill is named `drift-pr-review-loop` to avoid confusion with the existing `drift-pr-review` skill.

**Rationale**: `drift-pr-review` is a *reviewer* skill — it guides the agent when reviewing someone else's PR. `drift-pr-review-loop` is an *author automation* skill — it guides the agent that created a PR through the self-review + polling loop until approval. The two are complementary, not overlapping.

---

### 6. `work_artifacts/pr-loop-<PR>.json` gitignore status

**Decision**: Already gitignored. `.gitignore` line 44: `work_artifacts/` — the entire directory is ignored.

**Rationale**: No additional `.gitignore` entry needed. The state file will appear in `work_artifacts/pr-loop-42.json` for PR #42 and will not be tracked.

---

### 7. Windows compatibility

**Decision**: Implement engine as Python (`src/drift/pr_loop/`) with `subprocess` calls to `gh` CLI. No bash dependencies.

**Rationale**: This repo runs Windows-first (Windows runners in CI, Windows development machine per user context). A bash script engine would require WSL or Git Bash — fragile. Pure Python + `gh` CLI (which has Windows binaries) is fully cross-platform.

## Resolved Clarifications

| Clarification | Resolution |
|---|---|
| How to trigger Copilot Review | Poll for auto-response; Copilot code review must be enabled at repo level |
| `gh pr edit --add-reviewer` slug | Not required to trigger; bot auto-reviews if repo feature is enabled |
| Schema test impact | Regen `drift.schema.json` after `DriftConfig` change |
| Existing skill overlap | None — `drift-pr-review` = reviewer mode, `drift-pr-review-loop` = author loop mode |
| Windows compatibility | Python + `gh` CLI, no bash |
