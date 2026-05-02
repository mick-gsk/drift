"""Frozen Pydantic models for drift-cockpit Human Decision Cockpit (Feature 006)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DecisionStatus(StrEnum):
    """Exactly one status is active per PR at any time (FR-001)."""

    go = "go"
    go_with_guardrails = "go_with_guardrails"
    no_go = "no_go"
    # NOTE: missing evidence is represented as no_go, not a separate state
    # (per spec clarification 2026-05-01, fixing H3)


class OutcomeState(StrEnum):
    pending = "pending"
    captured = "captured"
    not_available = "not_available"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class RiskDriver(BaseModel, frozen=True):
    """A single prioritised risk driver in the Decision Panel (FR-002)."""

    driver_id: str
    title: str
    impact: float  # 0.0–1.0, higher = more impact on status
    severity: str
    source_refs: list[str] = Field(default_factory=list)


class GuardrailCondition(BaseModel, frozen=True):
    """A verifiable pre-merge condition for Guardrails/No-Go resolution (FR-008)."""

    condition_id: str
    description: str
    verification_method: str
    must_pass_before_merge: bool = True


class MinimalSafePlan(BaseModel, frozen=True):
    """Smallest action set that would bring the PR under the target threshold (FR-003/FR-004)."""

    plan_id: str
    pr_id: str
    steps: list[GuardrailCondition] = Field(default_factory=list)
    expected_risk_delta: float  # negative = risk reduction
    expected_score_delta: float  # positive = score improvement
    target_threshold: float
    feasible: bool = True


class AccountabilityCluster(BaseModel, frozen=True):
    """Groups PR changes by risk impact (FR-005)."""

    cluster_id: str
    pr_id: str
    label: str
    files: list[str] = Field(default_factory=list)
    risk_contribution: float  # 0.0–1.0, portion of total risk
    dominant_drivers: list[str] = Field(default_factory=list)


class OutcomeSnapshot(BaseModel, frozen=True):
    """Outcome state for a 7d or 30d window (FR-007/FR-014)."""

    window: str  # "7d" or "30d"
    state: OutcomeState = OutcomeState.pending
    rework_events: int | None = None
    merge_velocity_delta: float | None = None
    captured_at: datetime | None = None


# ---------------------------------------------------------------------------
# Core aggregate
# ---------------------------------------------------------------------------


class DecisionBundle(BaseModel, frozen=True):
    """Top-level aggregate: everything needed for one PR's Decision Panel (FR-001..FR-012)."""

    pr_id: str
    status: DecisionStatus
    confidence: float = Field(ge=0.0, le=1.0, description="Decision confidence (0.0–1.0)")
    evidence_sufficient: bool
    risk_score: float
    top_risk_drivers: list[RiskDriver] = Field(default_factory=list)
    safe_plans: list[MinimalSafePlan] = Field(default_factory=list)
    risk_clusters: list[AccountabilityCluster] = Field(default_factory=list)
    version: int = 1
    computed_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def missing_evidence_forces_no_go(self) -> DecisionBundle:
        if not self.evidence_sufficient and self.status != DecisionStatus.no_go:
            raise ValueError(
                "evidence_sufficient=False requires status=no_go (FR-011)"
            )
        return self


class LedgerEntry(BaseModel, frozen=True):
    """Append-only audit record for a PR's decision lifecycle (FR-006/FR-009/FR-013/FR-015)."""

    ledger_entry_id: str
    pr_id: str
    recommended_status: DecisionStatus
    human_status: DecisionStatus
    override_reason: str | None = None
    decision_actor: str
    evidence_refs: list[str] = Field(default_factory=list)
    outcome_7d: OutcomeSnapshot = Field(
        default_factory=lambda: OutcomeSnapshot(window="7d")
    )
    outcome_30d: OutcomeSnapshot = Field(
        default_factory=lambda: OutcomeSnapshot(window="30d")
    )
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def override_needs_reason(self) -> LedgerEntry:
        if (
            self.human_status != self.recommended_status
            and not self.override_reason
        ):
            raise ValueError(
                "override_reason must be set when human_status != recommended_status "
                "(FR-013, MissingOverrideJustificationError)"
            )
        return self
