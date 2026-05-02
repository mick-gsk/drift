"""Pure functions for the review loop state machine: T013-T033."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from drift_config._loader import PrLoopConfig
from drift_mcp.pr_loop._models import (
    LoopExitStatus,
    LoopState,
    ReviewComment,
    ReviewerVerdict,
    ReviewRound,
    ReviewState,
)


class PollTimeoutError(Exception):
    """Raised when reviewer polling exceeds poll_timeout_seconds."""

    def __init__(self, msg: str, verdicts: list[ReviewerVerdict] | None = None) -> None:
        super().__init__(msg)
        self.verdicts: list[ReviewerVerdict] = verdicts or []


# ---------------------------------------------------------------------------
# T013 — Self-review body builder (pure function)
# ---------------------------------------------------------------------------


def build_self_review_body(state: LoopState, gate_output: dict[str, Any]) -> str:
    """Build a structured markdown self-review comment from loop state and gate output."""
    lines = [
        f"## Self-Review — Round {state.round}",
        "",
        "### Gate Results",
        f"- Pre-commit: {'✓' if gate_output.get('pre_commit_passed') else '(not run)'}",
        f"- make check: {'✓' if gate_output.get('make_check_passed') else '(not run)'}",
        f"- make gate-check: {'✓' if gate_output.get('gate_check_passed') else '(not run)'}",
        "",
    ]
    changed_files: list[Any] = gate_output.get("changed_files") or []
    if changed_files:
        lines += ["### Files Changed", ""]
        for f in changed_files:
            lines.append(f"- `{f}`")
        lines.append("")
    drift_signals: list[Any] = gate_output.get("drift_signals") or []
    if drift_signals:
        lines += ["### Drift Signals", ""]
        for signal in drift_signals:
            lines.append(f"- {signal}")
        lines.append("")
    risks: list[Any] = gate_output.get("risks") or []
    if risks:
        lines += ["### Identified Risks", ""]
        for risk in risks:
            lines.append(f"- {risk}")
        lines.append("")
    lines += [
        "### Preliminary Verdict",
        "This diff appears structurally sound. Awaiting reviewer feedback.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T018 — poll_reviews
# ---------------------------------------------------------------------------


def poll_reviews(
    pr_number: int,
    config: PrLoopConfig,
    get_reviews_fn: Callable[[int], list[ReviewerVerdict]] | None = None,
) -> list[ReviewerVerdict]:
    """Poll GitHub until all configured reviewers have responded or timeout elapses."""
    from drift.pr_loop import _gh as gh

    get_reviews: Callable[[int], list[ReviewerVerdict]] = (
        get_reviews_fn if get_reviews_fn is not None else gh.get_reviews
    )
    deadline = time.monotonic() + config.poll_timeout_seconds
    configured = set(config.reviewers)
    while time.monotonic() < deadline:
        verdicts = get_reviews(pr_number)
        responded = {v.reviewer for v in verdicts if v.state != ReviewState.PENDING}
        if configured.issubset(responded):
            return verdicts
        time.sleep(config.poll_interval_seconds)
    # Timeout: mark non-responders as NO_RESPONSE
    verdicts = get_reviews(pr_number)
    responded_logins = {v.reviewer for v in verdicts}
    final: list[ReviewerVerdict] = list(verdicts)
    for reviewer in configured:
        if reviewer not in responded_logins:
            final.append(ReviewerVerdict(reviewer=reviewer, state=ReviewState.NO_RESPONSE))
    raise PollTimeoutError(f"Polling timed out after {config.poll_timeout_seconds}s", final)


# ---------------------------------------------------------------------------
# T020 — should_exit, should_escalate, detect_contradiction
# ---------------------------------------------------------------------------


def should_exit(
    verdicts: list[ReviewerVerdict],
    configured_reviewers: list[str],
) -> bool:
    """Return True when all configured reviewers APPROVED (NO_RESPONSE is skipped for exit)."""
    if not verdicts:
        return False
    verdict_map = {v.reviewer: v.state for v in verdicts}
    for reviewer in configured_reviewers:
        state = verdict_map.get(reviewer)
        if state is None or state == ReviewState.PENDING:
            return False
        if state == ReviewState.CHANGES_REQUESTED:
            return False
        # APPROVED or NO_RESPONSE both count as "done" for exit
    return True


def should_escalate(
    round_number: int,
    max_rounds: int,
    verdicts: list[ReviewerVerdict],
) -> bool:
    """Return True when max_rounds reached with any unresolved CHANGES_REQUESTED."""
    if round_number < max_rounds:
        return False
    return any(v.state == ReviewState.CHANGES_REQUESTED for v in verdicts)


def detect_contradiction(verdicts: list[ReviewerVerdict]) -> bool:
    """Return True when two verdicts for the same round directly conflict."""
    states = {v.state for v in verdicts}
    return ReviewState.APPROVED in states and ReviewState.CHANGES_REQUESTED in states


# ---------------------------------------------------------------------------
# T021 — next_loop_state
# ---------------------------------------------------------------------------


def next_loop_state(
    current: LoopState,
    round_result: ReviewRound,
    max_rounds: int,
    new_status: LoopExitStatus | None = None,
) -> LoopState:
    """Return a new LoopState with incremented round and appended ReviewRound."""
    if current.round > max_rounds:
        raise ValueError(f"round {current.round} exceeds max_rounds {max_rounds}")
    next_rounds = list(current.rounds) + [round_result]
    status = new_status if new_status is not None else current.status
    return current.model_copy(
        update={
            "round": current.round + 1,
            "rounds": next_rounds,
            "status": status,
        }
    )


# ---------------------------------------------------------------------------
# T024 + T031 — collect_unresolved_comments
# ---------------------------------------------------------------------------

_BOT_SUFFIX = "[bot]"
_KNOWN_BOTS = frozenset({"github-copilot[bot]", "dependabot[bot]"})


def collect_unresolved_comments(
    all_comments: list[ReviewComment],
    addressed_ids: list[str],
    configured_reviewers: list[str],
) -> list[ReviewComment]:
    """Return unresolved comments not yet addressed.

    Includes both reviewer comments and human comments (authors not in
    configured_reviewers and not a known bot). T031 extension.
    """
    addressed = set(addressed_ids)
    unresolved: list[ReviewComment] = []
    for comment in all_comments:
        if comment.id in addressed:
            continue
        if comment.resolved:
            continue
        # Include comments from configured reviewers or human authors (T031)
        is_reviewer = comment.author in configured_reviewers
        is_bot = comment.author in _KNOWN_BOTS or comment.author.endswith(_BOT_SUFFIX)
        is_human = not is_bot and not is_reviewer
        if is_reviewer or is_human:
            unresolved.append(comment)
    return unresolved


# ---------------------------------------------------------------------------
# T033 — self-review body update for human comments
# ---------------------------------------------------------------------------


def build_self_review_body_with_human_comments(
    state: LoopState,
    gate_output: dict[str, object],
    human_comments_addressed: list[ReviewComment],
    human_comments_deferred: list[ReviewComment],
) -> str:
    """Extend self-review body with human comment sections when relevant."""
    base = build_self_review_body(state, gate_output)
    sections: list[str] = []
    if human_comments_addressed:
        sections.append("\n### Human Comments Addressed This Round\n")
        for c in human_comments_addressed:
            sections.append(f"- `{c.id}` by **{c.author}**: {c.body[:80]}")
    if human_comments_deferred:
        sections.append("\n### Deferred Human Comments\n")
        for c in human_comments_deferred:
            sections.append(f"- `{c.id}` by **{c.author}**: {c.body[:80]}")
    return base + "\n".join(sections)


# ---------------------------------------------------------------------------
# T028 — loop_until_approved (full orchestration)
# ---------------------------------------------------------------------------


def loop_until_approved(
    pr_number: int,
    config: PrLoopConfig,
    artifacts_dir: Path,
    dry_run: bool = False,
) -> LoopState:
    """Drive the full review loop from initial state until APPROVED or ESCALATED.

    Side effects are isolated to _gh and _state modules.
    """
    from drift.pr_loop import _gh as gh
    from drift_mcp.pr_loop._state import load_loop_state, save_loop_state

    state = load_loop_state(pr_number, artifacts_dir)

    while state.status == LoopExitStatus.RUNNING and state.round <= config.max_rounds:
        # Step 1: Detect merge conflicts before gates
        if gh.detect_merge_conflicts():
            gh.post_conflict_report(pr_number, dry_run=dry_run)
            state = state.model_copy(update={"status": LoopExitStatus.ESCALATED})
            save_loop_state(state, artifacts_dir)
            return state

        # Step 2: Run local gates
        gate_result = gh.run_local_gates(dry_run=dry_run)

        # Step 3: Post self-review
        gate_output: dict[str, object] = {
            "pre_commit_passed": gate_result.passed,
            "make_check_passed": gate_result.passed,
            "gate_check_passed": gate_result.passed,
            "output": gate_result.output,
        }
        review_body = build_self_review_body(state, gate_output)
        review_comment_id = gh.post_self_review(pr_number, review_body, dry_run=dry_run)

        # Step 4: Request reviewers
        gh.request_reviewers(pr_number, config.reviewers, dry_run=dry_run)

        # Step 5: Poll for reviews
        try:
            verdicts = poll_reviews(pr_number, config)
        except PollTimeoutError as exc:
            verdicts = exc.verdicts if exc.verdicts else [
                ReviewerVerdict(reviewer=r, state=ReviewState.NO_RESPONSE)
                for r in config.reviewers
            ]

        # Step 6: Check for contradiction
        if detect_contradiction(verdicts):
            # Pause with escalation comment — mark ESCALATED
            all_comments = gh.get_pr_comments(pr_number)
            unresolved = collect_unresolved_comments(
                all_comments, list(state.addressed_comment_ids), config.reviewers
            )
            gh.post_escalation_summary(pr_number, unresolved, dry_run=dry_run)
            round_result = ReviewRound(
                round_number=state.round,
                push_sha="",
                self_review_comment_id=review_comment_id,
                verdicts=verdicts,
                unresolved_comments=unresolved,
            )
            state = next_loop_state(
                state, round_result, config.max_rounds, LoopExitStatus.ESCALATED
            )
            save_loop_state(state, artifacts_dir)
            return state

        # Step 7: Check exit condition
        if should_exit(verdicts, config.reviewers):
            round_result = ReviewRound(
                round_number=state.round,
                push_sha="",
                self_review_comment_id=review_comment_id,
                verdicts=verdicts,
                unresolved_comments=[],
            )
            state = next_loop_state(state, round_result, config.max_rounds, LoopExitStatus.APPROVED)
            save_loop_state(state, artifacts_dir)
            return state

        # Step 8: Collect unresolved comments and push fixes
        all_comments = gh.get_pr_comments(pr_number)
        unresolved = collect_unresolved_comments(
            all_comments, list(state.addressed_comment_ids), config.reviewers
        )

        if should_escalate(state.round, config.max_rounds, verdicts):
            gh.post_escalation_summary(pr_number, unresolved, dry_run=dry_run)
            round_result = ReviewRound(
                round_number=state.round,
                push_sha="",
                self_review_comment_id=review_comment_id,
                verdicts=verdicts,
                unresolved_comments=unresolved,
            )
            state = next_loop_state(
                state, round_result, config.max_rounds, LoopExitStatus.ESCALATED
            )
            save_loop_state(state, artifacts_dir)
            return state

        # Push fixes for unresolved comments
        new_addressed = list(state.addressed_comment_ids) + [c.id for c in unresolved]
        push_sha = gh.push_fix_commits(
            addressed_ids=[c.id for c in unresolved],
            round_number=state.round,
            dry_run=dry_run,
        )

        round_result = ReviewRound(
            round_number=state.round,
            push_sha=push_sha or "",
            self_review_comment_id=review_comment_id,
            verdicts=verdicts,
            unresolved_comments=unresolved,
        )
        state = next_loop_state(state, round_result, config.max_rounds)
        state = state.model_copy(update={"addressed_comment_ids": new_addressed})
        save_loop_state(state, artifacts_dir)

    # Fallback: escaped the loop without APPROVED
    if state.status == LoopExitStatus.RUNNING:
        state = state.model_copy(update={"status": LoopExitStatus.ESCALATED})
        save_loop_state(state, artifacts_dir)
    return state
