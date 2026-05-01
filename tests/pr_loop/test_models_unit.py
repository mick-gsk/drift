"""Unit tests for pr_loop Pydantic models (T009)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from drift.config._loader import PrLoopConfig
from drift.pr_loop._models import (
    LoopExitStatus,
    LoopState,
    ReviewComment,
    ReviewerVerdict,
    ReviewRound,
    ReviewState,
)

# ---------------------------------------------------------------------------
# PrLoopConfig validation
# ---------------------------------------------------------------------------


class TestPrLoopConfigValidation:
    def test_valid_defaults_accepted(self) -> None:
        cfg = PrLoopConfig(reviewers=["github-copilot[bot]"])
        assert cfg.max_rounds == 5
        assert cfg.poll_interval_seconds == 60
        assert cfg.poll_timeout_seconds == 600

    def test_max_rounds_minimum_one(self) -> None:
        with pytest.raises(ValidationError):
            PrLoopConfig(reviewers=["a"], max_rounds=0)

    def test_poll_interval_minimum_ten(self) -> None:
        with pytest.raises(ValidationError):
            PrLoopConfig(reviewers=["a"], poll_interval_seconds=9)

    def test_poll_timeout_must_exceed_interval(self) -> None:
        with pytest.raises(ValidationError):
            PrLoopConfig(reviewers=["a"], poll_interval_seconds=60, poll_timeout_seconds=60)

    def test_reviewers_must_be_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            PrLoopConfig(reviewers=[])

    def test_custom_values_accepted(self) -> None:
        cfg = PrLoopConfig(
            reviewers=["alice", "bob"],
            max_rounds=3,
            poll_interval_seconds=30,
            poll_timeout_seconds=300,
        )
        assert cfg.max_rounds == 3
        assert len(cfg.reviewers) == 2


# ---------------------------------------------------------------------------
# ReviewState enum completeness
# ---------------------------------------------------------------------------


class TestReviewStateEnum:
    def test_all_states_present(self) -> None:
        states = {s.value for s in ReviewState}
        assert "APPROVED" in states
        assert "CHANGES_REQUESTED" in states
        assert "PENDING" in states
        assert "NO_RESPONSE" in states

    def test_enum_has_exactly_four_members(self) -> None:
        assert len(ReviewState) == 4


# ---------------------------------------------------------------------------
# LoopExitStatus enum
# ---------------------------------------------------------------------------


class TestLoopExitStatusEnum:
    def test_all_statuses_present(self) -> None:
        statuses = {s.value for s in LoopExitStatus}
        assert "RUNNING" in statuses
        assert "APPROVED" in statuses
        assert "ESCALATED" in statuses
        assert "ERROR" in statuses


# ---------------------------------------------------------------------------
# LoopState round increments (frozen model)
# ---------------------------------------------------------------------------


class TestLoopStateModel:
    def _make_state(self, **kwargs: object) -> LoopState:
        defaults: dict[str, object] = {
            "pr_number": 42,
            "round": 1,
            "status": LoopExitStatus.RUNNING,
            "addressed_comment_ids": [],
            "rounds": [],
        }
        defaults.update(kwargs)
        return LoopState(**defaults)  # type: ignore[arg-type]

    def test_initial_state(self) -> None:
        state = self._make_state()
        assert state.pr_number == 42
        assert state.round == 1
        assert state.status == LoopExitStatus.RUNNING

    def test_frozen_model_rejects_mutation(self) -> None:
        state = self._make_state()
        with pytest.raises((TypeError, ValidationError)):
            state.round = 2  # type: ignore[misc]

    def test_model_copy_with_incremented_round(self) -> None:
        state = self._make_state(round=1)
        next_state = state.model_copy(update={"round": 2})
        assert next_state.round == 2
        assert state.round == 1  # original unchanged

    def test_addressed_comment_ids_can_grow(self) -> None:
        state = self._make_state(addressed_comment_ids=["id1"])
        updated = state.model_copy(update={"addressed_comment_ids": ["id1", "id2"]})
        assert len(updated.addressed_comment_ids) == 2


# ---------------------------------------------------------------------------
# ReviewerVerdict model
# ---------------------------------------------------------------------------


class TestReviewerVerdictModel:
    def test_verdict_with_approved_state(self) -> None:
        v = ReviewerVerdict(
            reviewer="github-copilot[bot]",
            state=ReviewState.APPROVED,
            submitted_at=None,
        )
        assert v.state == ReviewState.APPROVED

    def test_verdict_frozen(self) -> None:
        v = ReviewerVerdict(
            reviewer="alice",
            state=ReviewState.PENDING,
            submitted_at=None,
        )
        with pytest.raises((TypeError, ValidationError)):
            v.state = ReviewState.APPROVED  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ReviewRound model
# ---------------------------------------------------------------------------


class TestReviewRoundModel:
    def test_round_round_number(self) -> None:
        rr = ReviewRound(
            round_number=1,
            push_sha="abc1234",
            self_review_comment_id=None,
            verdicts=[],
            unresolved_comments=[],
        )
        assert rr.round_number == 1
        assert rr.push_sha == "abc1234"

    def test_round_frozen(self) -> None:
        rr = ReviewRound(
            round_number=1,
            push_sha="abc1234",
            self_review_comment_id=None,
            verdicts=[],
            unresolved_comments=[],
        )
        with pytest.raises((TypeError, ValidationError)):
            rr.round_number = 2  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ReviewComment model
# ---------------------------------------------------------------------------


class TestReviewCommentModel:
    def test_basic_comment(self) -> None:
        c = ReviewComment(
            id="node_id_123",
            author="github-copilot[bot]",
            body="Missing type annotation",
            path="src/drift/foo.py",
            line=42,
            resolved=False,
        )
        assert c.id == "node_id_123"
        assert not c.resolved

    def test_comment_without_file_path(self) -> None:
        c = ReviewComment(
            id="node_id_456",
            author="alice",
            body="General feedback",
            path=None,
            line=None,
            resolved=False,
        )
        assert c.path is None
        assert c.line is None
