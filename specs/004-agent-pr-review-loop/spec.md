# Feature Specification: Agent PR Review Loop

**Feature Branch**: `004-agent-pr-review-loop`
**Created**: 2026-04-30
**Status**: Draft → Clarified
**Input**: User description: "Ich möchte das folgender ablauf zur Routine wird: Ich beschreibe eine Aufgabe, starte den Agenten welcher die Aufgabe ausführt, dieser erstellt einen Pull Request. Um einen Pull Request abzuschließen, weisen wir den Agent an, seine eigenen Änderungen lokal zu überprüfen, zusätzliche spezifische Agentenüberprüfungen sowohl lokal als auch in der Cloud anzufordern, auf jegliches Feedback von Menschen oder Agenten zu reagieren und diesen Vorgang in einer Schleife zu wiederholen, bis alle Agentenüberprüfer zufrieden sind (im Prinzip eine Ralph-Wiggum-Schleife)."

## Clarifications

### Session 2026-04-30

- Q: Implementierungsform (wo lebt die Feature-Logik?) → A: Kombination — `scripts/` Python/Shell-Skript als ausführbare Engine + `.github/agents/` oder `.github/skills/` als Orchestrierungsschicht
- Q: Loop-Ausführungsmodell (wie wartet der Loop auf Reviewer-Antworten?) → A: Polling-Loop im Skript — wartet aktiv auf Reviewer-Antworten mit konfigurierbarem Timeout via `gh` CLI
- Q: Copilot Review auslösen (wie wird der Cloud-Reviewer angefordert?) → A: `gh` CLI / GitHub API — `github-copilot[bot]` als Reviewer explizit per Skript anfordern
- Q: Loop-Zustand persistieren (wo wird der Zustand zwischen Runden gespeichert?) → A: Temporäre JSON-Datei `work_artifacts/pr-loop-<PR-Nummer>.json`, gitignored
- Q: Konfigurationsort (wo leben Reviewer-Liste und max. Runden?) → A: Neuer Abschnitt `pr_loop:` in `drift.yaml`

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Agent completes a task and opens a reviewable PR (Priority: P1)

A developer describes a task in natural language. The agent executes the task, runs all local gates, and opens a Pull Request with a complete, self-reviewed diff. No human intervention is needed to get from task description to an open PR.

**Why this priority**: This is the entry point for every subsequent review step. Without a consistently well-structured, self-checked PR, the review loop cannot start.

**Independent Test**: Can be fully tested by having the agent execute a small, isolated code change and confirming that a GitHub PR exists, all local CI checks pass, and the PR description summarises the changes.

**Acceptance Scenarios**:

1. **Given** a task description is provided, **When** the agent completes the implementation, **Then** a PR is opened against the correct base branch with a conventional commit message and a filled PR description.
2. **Given** the agent has finished coding, **When** it prepares the PR, **Then** it runs `pre-commit run --all-files`, `make check`, and `make gate-check` locally before pushing, and the PR shows all checks green.
3. **Given** any local gate fails, **When** the agent encounters the failure, **Then** it fixes the root cause before opening the PR — it does not open a PR in a broken state.

---

### User Story 2 — Agent self-reviews its own diff and requests agent reviews (Priority: P1)

After opening the PR, the agent reads its own diff, writes a structured self-review comment on the PR, and then requests every configured agent reviewer (e.g. GitHub Copilot Review, cloud CI analysis). The loop does not advance until all agent reviewers have responded.

**Why this priority**: The self-review and agent-review request are the core loop initiators. Skipping them means human reviewers receive unscreened diffs.

**Independent Test**: Can be fully tested by confirming that after PR creation (a) a self-review comment appears on the PR, (b) each configured agent reviewer is requested, and (c) the agent blocks further action until reviewer responses arrive.

**Acceptance Scenarios**:

1. **Given** a PR is open, **When** the agent performs its self-review, **Then** a comment is posted to the PR that lists: files changed, signals triggered (drift analysis), any identified risks, and a preliminary approval verdict.
2. **Given** the self-review is posted, **When** agent reviewers are requested, **Then** each configured reviewer (GitHub Copilot Review, CI bot) is added to the review request list.
3. **Given** agent reviews are requested, **When** all reviewers have responded, **Then** their feedback (Approved / Changes Requested + comments) is collected before the next loop iteration begins.

---

### User Story 3 — Agent responds to review feedback in a loop until approved (Priority: P2)

When any agent reviewer requests changes, the agent reads every unresolved comment, addresses each one in a new commit, and re-requests reviews. This cycle repeats until all configured agent reviewers have approved, or a maximum number of rounds is reached and the issue is escalated to a human.

**Why this priority**: This is the "Ralph Wiggum loop" — the iterative closure mechanism. Without it, the loop is just a one-shot review.

**Independent Test**: Can be fully tested by injecting a synthetic "Changes Requested" review comment, confirming the agent produces a follow-up commit that addresses it, and verifying it re-requests the review without human intervention.

**Acceptance Scenarios**:

1. **Given** at least one reviewer has "Changes Requested", **When** the agent starts the next iteration, **Then** it reads every unresolved comment, produces commits that address each one, and pushes to the PR branch.
2. **Given** the agent has pushed fixes, **When** all previously requesting reviewers have now approved, **Then** the loop exits with a "ready for human review" status.
3. **Given** the maximum loop rounds are reached and agent reviewers still request changes, **When** the loop exits with unresolved feedback, **Then** the agent posts a summary comment listing all unresolved items and marks the PR for human escalation.

---

### User Story 4 — Human leaves a comment and the agent responds (Priority: P3)

A human reviewer leaves a comment on the open PR. The agent reads it, responds with a fix or a reasoned explanation, and continues the loop. Human approval remains the final gate.

**Why this priority**: Human feedback enriches the loop but is not required for the automated path to complete.

**Independent Test**: Can be fully tested by posting a comment manually to a test PR and confirming the agent produces a response commit or explanatory reply without re-opening unrelated work.

**Acceptance Scenarios**:

1. **Given** a human comment is posted, **When** the agent detects new unresolved comments, **Then** it addresses or explicitly defers each one with a written reason before pushing.
2. **Given** the agent has addressed human feedback, **When** all agent reviewers are satisfied, **Then** the PR is marked ready for final human approval.

---

### Edge Cases

- What happens when an agent reviewer becomes unavailable mid-loop (timeout, API error)? → Loop marks that reviewer as skipped for this round and proceeds; the skip is noted in the self-review comment.
- What happens when the agent's fix introduces a new CI failure? → The agent detects the new failure, reverts or fixes it, and re-runs all local gates before re-requesting reviews.
- What happens when two agent reviewers contradict each other? → The agent flags the contradiction in a PR comment, pauses the loop, and escalates to the human maintainer for resolution.
- What happens when the PR branch has merge conflicts? → The agent resolves merge conflicts (if straightforward) or posts a conflict report and pauses the loop pending human guidance.
- What happens when max rounds are reached but the PR is almost approved (1 minor comment)? → The loop still exits, posts the escalation summary, and does not force-merge.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: After completing a task, the agent MUST create a Pull Request targeting the correct base branch with a conventional commit message and a filled PR description derived from the task.
- **FR-002**: Before opening a PR, the agent MUST run all required local gates (`pre-commit run --all-files`, `make check`, `make gate-check`) and MUST NOT open the PR if any gate fails.
- **FR-003**: After opening the PR, the agent MUST post a structured self-review comment that covers: files changed, drift signals triggered, identified risks, and a preliminary verdict.
- **FR-004**: After the self-review, the agent MUST request `github-copilot[bot]` and any other configured reviewers via the GitHub API (`gh pr edit --add-reviewer` or equivalent REST call).
- **FR-005**: The loop engine MUST poll PR review state via `gh pr view --json reviews` at a configurable interval until all requested agent reviewers have responded or the polling timeout is reached.
- **FR-006**: When any agent reviewer requests changes, the agent MUST read all unresolved comments, produce commits addressing each one, push to the PR branch, and re-request reviews.
- **FR-007**: The loop MUST exit when all configured agent reviewers have approved the PR.
- **FR-008**: The loop MUST also exit when a configurable maximum number of review rounds (configured under `pr_loop.max_rounds` in `drift.yaml`) is reached; in that case the agent MUST post an escalation summary listing all unresolved items.
- **FR-009**: When a human comment is detected, the agent MUST respond to or explicitly defer it before the next push.
- **FR-010**: The agent MUST NOT merge the PR; merging remains the exclusive right of the human maintainer.
- **FR-011**: Every loop iteration MUST be traceable: the agent MUST reference which comments it addressed in each commit message or PR reply.
- **FR-012**: The loop engine MUST persist its state to `work_artifacts/pr-loop-<PR-number>.json` (gitignored) after each round so the loop can be resumed if the process is interrupted.
- **FR-013**: The feature MUST be implemented as: (a) a `scripts/pr_review_loop.py` thin entry-point (`sys.exit(main())`) that delegates all logic to `src/drift/pr_loop/`; the engine MUST reside in the library, NOT in the script; and (b) a `.github/skills/drift-pr-review-loop/SKILL.md` orchestration layer that the Copilot agent uses to invoke the engine and interpret results.
- **FR-014**: When the PR branch has merge conflicts, the agent MUST detect them before each gate run. For purely mechanical conflicts (whitespace, adjacent non-overlapping hunks), the agent MAY attempt auto-resolution via `git merge`; for semantic conflicts, the agent MUST post a conflict-report comment on the PR, set `LoopState.status = ESCALATED`, and pause the loop without pushing further commits.

### Key Entities

- **PR Review Round**: One complete pass of self-review → agent-review request → polling wait → feedback collection → fix commits. Each round has a sequence number, a list of reviewers, and a verdict per reviewer.
- **Agent Reviewer**: A configurable participant in the review loop defined under `pr_loop.reviewers` in `drift.yaml`. Primary reviewer: `github-copilot[bot]`, triggered via GitHub API. Has a name, trigger method, and response type (Approved / Changes Requested / No Response).
- **Review Comment**: A single unit of feedback attached to a specific file/line or the PR thread. Has an author (human or agent), a resolution status, and — after the agent responds — a linked commit or reply.
- **Loop Exit Condition**: Either "all configured agent reviewers approved" or "`pr_loop.max_rounds` reached". Determines whether the PR exits into "ready for human review" or "escalated" state.
- **Self-Review Artefact**: The structured comment the agent posts after each push. Contains the drift analysis result, gate outcomes, comment resolution list, and loop state.
- **Loop State File**: `work_artifacts/pr-loop-<PR-number>.json` — gitignored JSON file written by `scripts/pr_review_loop.py` after each round. Contains: PR number, current round index, reviewer verdicts, list of addressed comment IDs, and loop exit status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every agent-created PR that enters the review loop exits with either full agent-reviewer approval or a complete escalation summary — zero PRs are silently abandoned mid-loop.
- **SC-002**: The feedback-response cycle completes without manual intervention for PRs where only technical issues (failing tests, lint, gate violations) are found.
- **SC-003**: The number of review rounds never exceeds the configured maximum; the loop always terminates.
- **SC-004**: Every agent-reviewer comment on a PR is either addressed by a commit or explicitly deferred with a written reason — zero silently ignored comments at loop exit.
- **SC-005**: Human reviewers consistently rate the self-review comment as "useful context" (captures changes, risks, and drift findings) in at least 80% of PR reviews.
- **SC-006**: The average time from task description to "ready for human review" decreases compared to the baseline manual workflow.

## Assumptions

- GitHub Pull Requests are the canonical review mechanism for this repo; all review state is tracked via GitHub PR reviews and comments.
- "Cloud agent reviews" means requesting `github-copilot[bot]` (and any other reviewer listed under `pr_loop.reviewers` in `drift.yaml`) via the GitHub API; these are triggered by the script calling `gh pr edit --add-reviewer`, not by separate manual steps.
- "Local agent reviews" means automated gate scripts (`pre-commit`, `make check`, `make gate-check`, `drift analyze`) that run on the agent's local machine before and after each push.
- Reviewer list and maximum loop rounds are configured under a new `pr_loop:` section in `drift.yaml`; sensible defaults (1 reviewer: `github-copilot[bot]`, max 5 rounds, poll interval 60 s) are provided so the feature works out-of-the-box.
- Loop state is persisted to `work_artifacts/pr-loop-<PR-number>.json` (gitignored); this file is created by `scripts/pr_review_loop.py` and read by the SKILL orchestration layer.
- Human approval is the final merge gate and is explicitly outside the automated loop — the loop only drives the PR to a "ready for human review" state.
- The agent has read/write access to the GitHub PR (can post comments, request reviewers, push commits) via an authenticated `gh` CLI session (no additional token setup required beyond existing repo auth).
- Merge conflicts that require semantic understanding are escalated to the human rather than auto-resolved.
- The workflow applies to all PRs created by agents in this repo; manually created PRs are out of scope for v1.
