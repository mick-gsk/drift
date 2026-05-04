from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class FeedbackAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CLARIFY = "clarify"
    AMEND = "amend"
    ADD_FEATURE = "add_feature"

class CapturedIntent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    intent_id: str
    raw: str
    summary: str
    required_features: list[str]
    output_type: str
    confidence: float
    clarification_needed: bool
    # Legacy fields
    raw_query: str = ""
    intent_type: str = ""
    features: dict[str, Any] = {}
    needs_clarification: bool = False
    clarification_question: str | None = None

class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: str
    confidence: float
    missing: list[str]
    agent_feedback: str
    iteration: int = 1
    # Legacy fields
    is_safe: bool = True
    risk_score: float = 0.0
    reasoning: str = ""

class FeedbackActionItem(BaseModel):
    priority: int
    action: str
    description: str

class FeedbackResult(BaseModel):
    actions: list[FeedbackActionItem]
    estimated_complexity: str
    # Legacy fields
    action: FeedbackAction = FeedbackAction.APPROVE
    comment: str | None = None
    updated_intent: dict[str, Any] | None = None
