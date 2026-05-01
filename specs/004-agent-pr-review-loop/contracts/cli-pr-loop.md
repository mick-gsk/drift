# CLI Contract: `drift pr-loop`

**Phase 1 Output** | **Date**: 2026-04-30 | **Plan**: [../plan.md](../plan.md)

## Command Signature

```
drift pr-loop <PR_NUMBER> [OPTIONS]
```

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `PR_NUMBER` | integer | yes | GitHub Pull Request number to drive through the review loop |

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--repo` | string | auto-detect from `git remote` | GitHub repo in `owner/repo` format |
| `--config` | path | `drift.yaml` in cwd | Path to drift config file |
| `--format` | choice: `rich`, `json` | `rich` | Output format |
| `--dry-run` | flag | false | Run all local checks and post self-review but do not request reviewers or push fixes |
| `--exit-zero` | flag | false | Always exit 0 (for CI pipelines that capture output separately) |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Loop exited with `APPROVED` status |
| 1 | Loop exited with `ESCALATED` status (max rounds reached) |
| 2 | Loop exited with `ERROR` status (unrecoverable failure) |
| 3 | Precondition failure (PR not found, not authenticated, local gates failed) |

## Standard Output (Rich format)

```
PR #42 — Agent Review Loop
──────────────────────────
Round 1/5
  ✓ Local gates passed (pre-commit, make check, make gate-check)
  ✓ Self-review posted (comment #12345678)
  ✓ Reviewer requested: github-copilot[bot]
  ⏳ Polling for reviews... (60s interval, timeout 600s)
  ✓ github-copilot[bot]: APPROVED

Loop exited: APPROVED after 1 round(s)
PR #42 is ready for human review.
```

```
PR #42 — Agent Review Loop
──────────────────────────
Round 3/5
  ✓ Local gates passed
  ✓ Self-review posted (comment #12345682)
  ✓ Reviewer re-requested: github-copilot[bot]
  ⏳ Polling...
  ✗ github-copilot[bot]: CHANGES_REQUESTED
    Unresolved comments: 2

  Addressing comment #abc123: "Missing type annotation on `run()`"
  Addressing comment #def456: "Test coverage for error path"
  ✓ Fix commit pushed: a1b2c3d

Round 4/5
  ...

Loop exited: ESCALATED (max 5 rounds reached)
Escalation summary posted to PR #42.
```

## Standard Output (JSON format)

```json
{
  "pr_number": 42,
  "status": "APPROVED",
  "rounds_completed": 1,
  "rounds_max": 5,
  "reviewers": ["github-copilot[bot]"],
  "verdicts": [
    {"reviewer": "github-copilot[bot]", "state": "APPROVED", "round": 1}
  ],
  "escalated": false,
  "loop_state_file": "work_artifacts/pr-loop-42.json"
}
```

## Preconditions (checked before loop starts)

1. `gh auth status` — authenticated GitHub CLI session present
2. PR `<PR_NUMBER>` exists and is open in the configured repo
3. Current branch HEAD matches the PR's head branch (or `--dry-run` is set)
4. Local gates pass: `pre-commit run --all-files`, `make check`, `make gate-check`

If any precondition fails, the command exits with code 3 and a human-readable error on stderr.

## `drift.yaml` Config Contract

```yaml
pr_loop:
  reviewers:
    - github-copilot[bot]    # list of reviewer logins to request and await
  max_rounds: 5              # maximum loop iterations before escalation
  poll_interval_seconds: 60  # how often to check review state (min: 10)
  poll_timeout_seconds: 600  # max wait per reviewer per round
```

## Invariants

- The command NEVER merges the PR.
- The command NEVER pushes to a branch that is not the PR's head branch.
- The command NEVER opens a new PR — it requires an existing open PR number.
- The `--dry-run` flag prevents any writes to GitHub (no comments, no pushes, no review requests).
