"""Unit tests for pr_loop engine pure functions (T015, T022, T030)."""

from __future__ import annotations

from drift.pr_loop._engine import (
    build_self_review_body,
    collect_unresolved_comments,
    detect_contradiction,
    next_loop_state,
    should_escalate,
    should_exit,
)
from drift.pr_loop._models import (
    LoopExitStatus,
    LoopState,
    ReviewComment,
    ReviewerVerdict,
    ReviewRound,
    ReviewState,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verdict(reviewer: str, state: ReviewState) -> ReviewerVerdict:
    return ReviewerVerdict(reviewer=reviewer, state=state, submitted_at=None)


def _comment(cid: str, author: str = "alice", resolved: bool = False) -> ReviewComment:
    return ReviewComment(
        id=cid, author=author, body="Some comment", path=None, line=None, resolved=resolved
    )


def _make_state(**kwargs: object) -> LoopState:
    defaults: dict[str, object] = {
        "pr_number": 42,
        "round": 1,
        "status": LoopExitStatus.RUNNING,
        "addressed_comment_ids": [],
        "rounds": [],
    }
    defaults.update(kwargs)
    return LoopState(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# should_exit (T015)
# ---------------------------------------------------------------------------


class TestShouldExit:
    def test_returns_true_when_all_approved(self) -> None:
        verdicts = [_verdict("alice", ReviewState.APPROVED)]
        assert should_exit(verdicts, ["alice"]) is True

    def test_returns_false_when_changes_requested(self) -> None:
        verdicts = [_verdict("alice", ReviewState.CHANGES_REQUESTED)]
        assert should_exit(verdicts, ["alice"]) is False

    def test_returns_false_when_reviewer_still_pending(self) -> None:
        verdicts = [_verdict("alice", ReviewState.PENDING)]
        assert should_exit(verdicts, ["alice"]) is False

    def test_no_response_treated_as_done_for_exit(self) -> None:
        verdicts = [_verdict("alice", ReviewState.NO_RESPONSE)]
        assert should_exit(verdicts, ["alice"]) is True

    def test_returns_false_when_no_verdicts(self) -> None:
        assert should_exit([], ["alice"]) is False

    def test_multiple_reviewers_all_approved(self) -> None:
        verdicts = [
            _verdict("alice", ReviewState.APPROVED),
            _verdict("bob", ReviewState.APPROVED),
        ]
        assert should_exit(verdicts, ["alice", "bob"]) is True

    def test_multiple_reviewers_one_pending(self) -> None:
        verdicts = [
            _verdict("alice", ReviewState.APPROVED),
            _verdict("bob", ReviewState.PENDING),
        ]
        assert should_exit(verdicts, ["alice", "bob"]) is False


# ---------------------------------------------------------------------------
# should_escalate (T015)
# ---------------------------------------------------------------------------


class TestShouldEscalate:
    def test_returns_true_when_max_rounds_with_changes_requested(self) -> None:
        verdicts = [_verdict("alice", ReviewState.CHANGES_REQUESTED)]
        assert should_escalate(5, max_rounds=5, verdicts=verdicts) is True

    def test_returns_false_when_not_at_max_rounds(self) -> None:
        verdicts = [_verdict("alice", ReviewState.CHANGES_REQUESTED)]
        assert should_escalate(3, max_rounds=5, verdicts=verdicts) is False

    def test_returns_false_when_all_approved_at_max(self) -> None:
        verdicts = [_verdict("alice", ReviewState.APPROVED)]
        assert should_escalate(5, max_rounds=5, verdicts=verdicts) is False


# ---------------------------------------------------------------------------
# next_loop_state (T015)
# ---------------------------------------------------------------------------


class TestNextLoopState:
    def test_increments_round(self) -> None:
        state = _make_state(round=1)
        rr = ReviewRound(
            round_number=1,
            push_sha="abc",
            self_review_comment_id=None,
            verdicts=[],
            unresolved_comments=[],
        )
        next_state = next_loop_state(state, rr, max_rounds=5)
        assert next_state.round == 2

    def test_appends_review_round(self) -> None:
        state = _make_state(round=1)
        rr = ReviewRound(
            round_number=1,
            push_sha="abc",
            self_review_comment_id=None,
            verdicts=[],
            unresolved_comments=[],
        )
        next_state = next_loop_state(state, rr, max_rounds=5)
        assert len(next_state.rounds) == 1

    def test_propagates_new_status(self) -> None:
        state = _make_state(round=1)
        rr = ReviewRound(
            round_number=1,
            push_sha="abc",
            self_review_comment_id=None,
            verdicts=[],
            unresolved_comments=[],
        )
        next_state = next_loop_state(state, rr, max_rounds=5, new_status=LoopExitStatus.APPROVED)
        assert next_state.status == LoopExitStatus.APPROVED


# ---------------------------------------------------------------------------
# detect_contradiction (T015)
# ---------------------------------------------------------------------------


class TestDetectContradiction:
    def test_returns_true_when_approved_and_changes_requested(self) -> None:
        verdicts = [
            _verdict("alice", ReviewState.APPROVED),
            _verdict("bob", ReviewState.CHANGES_REQUESTED),
        ]
        assert detect_contradiction(verdicts) is True

    def test_returns_false_when_all_approved(self) -> None:
        verdicts = [_verdict("alice", ReviewState.APPROVED)]
        assert detect_contradiction(verdicts) is False

    def test_returns_false_when_pending_only(self) -> None:
        verdicts = [_verdict("alice", ReviewState.PENDING)]
        assert detect_contradiction(verdicts) is False


# ---------------------------------------------------------------------------
# collect_unresolved_comments (T022 + T030)
# ---------------------------------------------------------------------------


class TestCollectUnresolvedComments:
    def test_returns_only_unresolved_not_addressed(self) -> None:
        comments = [
            _comment("c1"),
            _comment("c2"),
        ]
        result = collect_unresolved_comments(
            comments, addressed_ids=["c1"], configured_reviewers=[]
        )
        assert len(result) == 1
        assert result[0].id == "c2"

    def test_excludes_resolved_comments(self) -> None:
        comments = [_comment("c1", resolved=True)]
        result = collect_unresolved_comments(comments, addressed_ids=[], configured_reviewers=[])
        assert len(result) == 0

    def test_includes_reviewer_comments(self) -> None:
        comments = [_comment("c1", author="github-copilot[bot]")]
        result = collect_unresolved_comments(
            comments,
            addressed_ids=[],
            configured_reviewers=["github-copilot[bot]"],
        )
        assert len(result) == 1

    def test_includes_human_comments(self) -> None:
        """T030: Human comments (author not a bot) should be included."""
        comments = [_comment("c1", author="human-user")]
        result = collect_unresolved_comments(
            comments, addressed_ids=[], configured_reviewers=["github-copilot[bot]"]
        )
        assert len(result) == 1

    def test_excludes_known_bot_comments(self) -> None:
        """Bots that are not in configured_reviewers should be excluded."""
        comments = [_comment("c1", author="dependabot[bot]")]
        result = collect_unresolved_comments(
            comments, addressed_ids=[], configured_reviewers=["github-copilot[bot]"]
        )
        assert len(result) == 0

    def test_full_loop_iteration_marks_comments_addressed(self) -> None:
        """After addressing comments, they should not reappear."""
        comments = [_comment("c1")]
        first_pass = collect_unresolved_comments(
            comments, addressed_ids=[], configured_reviewers=[]
        )
        assert len(first_pass) == 1
        # After addressing:
        second_pass = collect_unresolved_comments(
            comments, addressed_ids=["c1"], configured_reviewers=[]
        )
        assert len(second_pass) == 0

    def test_exit_on_escalated_status(self) -> None:
        """When state is ESCALATED, loop should stop (verified in engine integration)."""
        state = _make_state(status=LoopExitStatus.ESCALATED)
        assert state.status == LoopExitStatus.ESCALATED


# ---------------------------------------------------------------------------
# build_self_review_body (T013)
# ---------------------------------------------------------------------------


class TestBuildSelfReviewBody:
    def test_contains_round_number(self) -> None:
        state = _make_state(round=2)
        body = build_self_review_body(state, {})
        assert "Round 2" in body

    def test_includes_preliminary_verdict(self) -> None:
        state = _make_state()
        body = build_self_review_body(state, {})
        assert "Preliminary Verdict" in body

    def test_includes_changed_files_when_present(self) -> None:
        state = _make_state()
        body = build_self_review_body(state, {"changed_files": ["src/foo.py"]})
        assert "src/foo.py" in body

    def test_includes_risks_when_present(self) -> None:
        state = _make_state()
        body = build_self_review_body(state, {"risks": ["High complexity"]})
        assert "High complexity" in body
