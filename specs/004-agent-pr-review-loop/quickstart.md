# Quickstart: drift pr-loop

`drift pr-loop` drives a GitHub PR through an automated agent review loop.

---

## 1. Prerequisites

### Install drift (dev version in workspace)
```bash
pip install -e '.[dev]'
drift --version
```

### Authenticate gh CLI
```bash
gh auth login
gh auth status
```

---

## 2. Configure drift.yaml

Add a `pr_loop:` section to your `drift.yaml`:

```yaml
pr_loop:
  reviewers:
    - github-copilot[bot]
  max_rounds: 5
  poll_interval_seconds: 60
  poll_timeout_seconds: 600
```

**Fields**:
- `reviewers` (required): GitHub handles of automated reviewers to request and wait for
- `max_rounds` (default: 5): Maximum review–fix iterations before escalating
- `poll_interval_seconds` (default: 60): How often to poll for new reviews
- `poll_timeout_seconds` (default: 600): Max wait per poll round before giving up

---

## 3. Run the loop

```bash
# Dry-run: verify behavior without any GitHub side-effects
drift pr-loop 42 --dry-run

# Full run: posts self-review, requests reviewers, polls, iterates
drift pr-loop 42

# JSON output (machine-readable)
drift pr-loop 42 --format json | jq .status
```

---

## 4. Exit Codes

| Code | Status | Meaning |
|------|--------|---------|
| `0` | APPROVED | All reviewers approved — safe to merge |
| `1` | ESCALATED | Max rounds reached or unresolvable conflict |
| `2` | ERROR | Loop failed unexpectedly |
| `3` | Precondition | gh CLI not authenticated or `pr_loop:` missing |

---

## 5. State Artifact

Each run persists state to `work_artifacts/pr-loop-<PR_NUMBER>.json`:

```json
{
  "pr_number": 42,
  "round": 3,
  "status": "APPROVED",
  "addressed_comment_ids": ["1234", "5678"]
}
```

This file is gitignored and used for crash recovery.

---

## 6. Skill Reference

See `.github/skills/drift-pr-review-loop/SKILL.md` for advanced usage,
escalation handling, and troubleshooting.
