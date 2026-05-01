# Data Model: Agent PR Review Loop

**Phase 1 Output** | **Date**: 2026-04-30 | **Plan**: [plan.md](plan.md)

## Entities & Relationships

```
DriftConfig
  └── pr_loop: PrLoopConfig | None
        ├── reviewers: list[str]          # e.g. ["github-copilot[bot]"]
        ├── max_rounds: int               # default: 5
        ├── poll_interval_seconds: int    # default: 60
        └── poll_timeout_seconds: int     # default: 600

LoopState                                 # persisted to work_artifacts/pr-loop-<PR>.json
  ├── pr_number: int
  ├── round: int                          # 1-based, current round
  ├── status: LoopExitStatus
  ├── addressed_comment_ids: list[str]    # GitHub comment node IDs already handled
  └── rounds: list[ReviewRound]

ReviewRound
  ├── round_number: int
  ├── push_sha: str                       # Git SHA of the HEAD at this round's push
  ├── self_review_comment_id: str | None  # GitHub comment ID of the posted self-review
  ├── verdicts: list[ReviewerVerdict]
  └── unresolved_comments: list[ReviewComment]

ReviewerVerdict
  ├── reviewer: str                       # reviewer login, e.g. "github-copilot[bot]"
  ├── state: ReviewState                  # APPROVED | CHANGES_REQUESTED | PENDING | NO_RESPONSE
  └── submitted_at: datetime | None

ReviewComment
  ├── id: str                             # GitHub comment node ID
  ├── author: str
  ├── body: str
  ├── path: str | None                    # file path if inline comment
  ├── line: int | None
  └── resolved: bool

LoopExitStatus (enum)
  ├── RUNNING
  ├── APPROVED          # all configured reviewers APPROVED
  ├── ESCALATED         # max_rounds reached with unresolved items
  └── ERROR             # unrecoverable failure (e.g. push rejected)

ReviewState (enum)
  ├── APPROVED
  ├── CHANGES_REQUESTED
  ├── PENDING           # reviewer added but no response yet
  └── NO_RESPONSE       # timeout elapsed without response
```

## Validation Rules

- `PrLoopConfig.max_rounds` must be ≥ 1
- `PrLoopConfig.poll_interval_seconds` must be ≥ 10
- `PrLoopConfig.poll_timeout_seconds` must be > `poll_interval_seconds`
- `PrLoopConfig.reviewers` must be non-empty (if `pr_loop:` section is present)
- `LoopState.round` must be ≤ `PrLoopConfig.max_rounds` at write time

## State Transitions

```
RUNNING ──(all reviewers APPROVED)──────────────────► APPROVED
RUNNING ──(round == max_rounds, unresolved exist)───► ESCALATED
RUNNING ──(push rejected / gh CLI error)────────────► ERROR
```

## Default Values (`drift.yaml`)

```yaml
pr_loop:
  reviewers:
    - github-copilot[bot]
  max_rounds: 5
  poll_interval_seconds: 60
  poll_timeout_seconds: 600
```

## Source Module Mapping

| Entity | Module |
|--------|--------|
| `PrLoopConfig` | `src/drift/config/_loader.py` (added field on `DriftConfig`) |
| `LoopState`, `ReviewRound`, `ReviewerVerdict`, `ReviewComment`, `LoopExitStatus`, `ReviewState` | `src/drift/pr_loop/_models.py` |
| State I/O (`load_loop_state`, `save_loop_state`) | `src/drift/pr_loop/_state.py` |
| Polling engine (`poll_reviews`, `collect_unresolved_comments`) | `src/drift/pr_loop/_engine.py` |
| GitHub side-effects (`post_self_review`, `request_reviewers`, `post_escalation_summary`) | `src/drift/pr_loop/_gh.py` |
| CLI subcommand | `src/drift/pr_loop/_cmd.py` |
| Public API re-exports | `src/drift/pr_loop/__init__.py` |
| Thin script entry point | `scripts/pr_review_loop.py` |
| Copilot orchestration | `.github/skills/drift-pr-review-loop/SKILL.md` |
