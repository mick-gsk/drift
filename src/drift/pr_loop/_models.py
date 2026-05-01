"""Frozen Pydantic models for the PR review loop (T008)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class ReviewState(StrEnum):
    """State of a single reviewer's response."""

    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    PENDING = "PENDING"
    NO_RESPONSE = "NO_RESPONSE"


class LoopExitStatus(StrEnum):
    """Overall exit status of the review loop."""

    RUNNING = "RUNNING"
    APPROVED = "APPROVED"
    ESCALATED = "ESCALATED"
    ERROR = "ERROR"


class ReviewComment(BaseModel):
    """A single comment on the PR (inline or general)."""

    model_config = ConfigDict(frozen=True)

    id: str
    author: str
    body: str
    path: str | None = None
    line: int | None = None
    resolved: bool = False


class ReviewerVerdict(BaseModel):
    """One reviewer's verdict for a round."""

    model_config = ConfigDict(frozen=True)

    reviewer: str
    state: ReviewState
    submitted_at: datetime | None = None


class ReviewRound(BaseModel):
    """Snapshot of a single review round."""

    model_config = ConfigDict(frozen=True)

    round_number: int
    push_sha: str
    self_review_comment_id: str | None = None
    verdicts: list[ReviewerVerdict] = []
    unresolved_comments: list[ReviewComment] = []


class LoopState(BaseModel):
    """Full loop state, persisted to work_artifacts/pr-loop-<PR>.json."""

    model_config = ConfigDict(frozen=True)

    pr_number: int
    round: int = 1
    status: LoopExitStatus = LoopExitStatus.RUNNING
    addressed_comment_ids: list[str] = []
    rounds: list[ReviewRound] = []
