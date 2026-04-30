# Skill: drift-pr-review-loop

## Description

Drives a GitHub PR through an automated agent review loop using `drift pr-loop`.
Covers preconditions, command usage, exit code interpretation, escalation handling,
and dry-run workflows.

**Trigger words**: pr-loop, review loop, agent review, automated review, PR review loop

---

## Preconditions

Before running `drift pr-loop`, verify:

1. **gh CLI authenticated**: `gh auth status` must succeed. If not, run `gh auth login`.
2. **drift.yaml has pr_loop section**: Minimum required config:
   ```yaml
   pr_loop:
     reviewers:
       - github-copilot[bot]
     max_rounds: 5
     poll_interval_seconds: 60
     poll_timeout_seconds: 600
   ```
3. **On a feature branch**: The command pushes fix commits; ensure you are not on `main`/`master`.

---

## Step 1: Run the loop

```bash
drift pr-loop <PR_NUMBER> [OPTIONS]
```

**Options**:

| Option | Default | Purpose |
|--------|---------|---------|
| `--repo owner/repo` | auto-detected | Override GitHub repo |
| `--config PATH` | `drift.yaml` | Config file path |
| `--format rich\|json` | `rich` | Output format |
| `--dry-run` | false | No GitHub side-effects |
| `--exit-zero` | false | Always exit 0 |

**Example**:
```bash
drift pr-loop 42 --dry-run   # Verify without side-effects
drift pr-loop 42              # Full run
drift pr-loop 42 --format json | jq .status  # Machine-readable
```

---

## Step 2: Exit Code Interpretation

| Exit Code | Meaning | Agent Action |
|-----------|---------|--------------|
| `0` | APPROVED — all reviewers approved | Proceed to merge or close loop |
| `1` | ESCALATED — max rounds reached or unresolved conflict | Notify maintainer, do not merge |
| `2` | ERROR — loop failed unexpectedly | Check logs, fix root cause, re-run |
| `3` | Precondition failed | Run `gh auth login` or add `pr_loop:` to drift.yaml |

---

## Step 3: Escalation Handling

When exit code is `1` (ESCALATED):
- A PR comment has been posted listing all unresolved comments/verdicts
- The state file is saved to `work_artifacts/pr-loop-<PR_NUMBER>.json`
- **Do not force-merge** — notify the human maintainer
- Inspect the JSON state for `escalation_reason`:
  ```bash
  cat work_artifacts/pr-loop-42.json | jq .escalation_reason
  ```

---

## Step 4: Dry-Run Verification

Before running in production, use `--dry-run` to verify the loop logic:
```bash
drift pr-loop 42 --dry-run --format json
```
No `gh pr comment`, `git push`, or `gh pr request-reviewers` calls will be made.
State is NOT written to `work_artifacts/`.

---

## References

- Spec: `specs/004-agent-pr-review-loop/spec.md` (FR-001–FR-013)
- Config schema: `drift.schema.json` → `pr_loop` section
- State artifact: `work_artifacts/pr-loop-<PR_NUMBER>.json`
- Engine: `src/drift/pr_loop/_engine.py`
- Side-effects: `src/drift/pr_loop/_gh.py`
