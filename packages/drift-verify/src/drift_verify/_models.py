"""Frozen Pydantic models for drift-verify Evidence Package (Feature 005)."""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class ViolationType(StrEnum):
    layer_violation = "layer_violation"
    forbidden_dependency = "forbidden_dependency"
    file_placement = "file_placement"
    naming_convention = "naming_convention"
    rule_conflict = "rule_conflict"


class Verdict(StrEnum):
    automerge = "automerge"
    needs_fix = "needs_fix"
    needs_review = "needs_review"
    escalate_to_human = "escalate_to_human"


class EvidenceFlag(StrEnum):
    no_changes_detected = "no_changes_detected"
    rule_conflict = "rule_conflict"
    independent_review_unavailable = "independent_review_unavailable"


class Severity(StrEnum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ChangeSet(BaseModel, frozen=True):
    """The change to be verified. Passed by the caller."""

    diff_text: str = ""
    changed_files: list[Path] = Field(default_factory=list)
    spec_path: Path | None = None
    repo_path: Path = Field(default_factory=Path)
    author: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ViolationFinding(BaseModel, frozen=True):
    """Single architecture or structural rule violation."""

    violation_type: ViolationType
    severity: Severity
    file: str | None = None
    line: int | None = None
    rule_id: str | None = None
    conflicting_rule_id: str | None = None
    message: str
    remediation: str

    @model_validator(mode="after")
    def rule_conflict_needs_conflicting_id(self) -> ViolationFinding:
        if (
            self.violation_type == ViolationType.rule_conflict
            and self.conflicting_rule_id is None
        ):
            raise ValueError(
                "conflicting_rule_id must be set for rule_conflict violations"
            )
        return self


class ActionRecommendation(BaseModel, frozen=True):
    """Machine-readable verdict."""

    verdict: Verdict
    reason: str
    blocking_violation_count: int = 0


class FunctionalEvidence(BaseModel, frozen=True):
    """Caller-provided functional/CI evidence (FR-006)."""

    tests_passed: bool | None = None
    tests_total: int | None = None
    tests_failing: int | None = None
    lint_passed: bool | None = None
    typecheck_passed: bool | None = None
    screenshots: list[str] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    metrics: dict[str, float] = Field(default_factory=dict)


class IndependentReviewResult(BaseModel, frozen=True):
    """Result from reviewer agent (synchronous; unavailable on timeout)."""

    available: bool
    confidence_delta: float = 0.0
    findings: list[str] = Field(default_factory=list)
    spec_criteria_violated: list[str] = Field(default_factory=list)


class RulePromotionProposal(BaseModel, frozen=True):
    """Proposal to permanently add a rule based on recurring violations."""

    pattern_key: str
    occurrence_count: int
    threshold: int
    suggested_rule_id: str
    suggested_description: str
    affected_files: list[str] = Field(default_factory=list)


class PatternHistoryEntry(BaseModel, frozen=True):
    """Persisted entry for rule promotion counter (JSONL)."""

    type: str
    pattern: str
    file: str
    ts: str


class EvidencePackage(BaseModel, frozen=True):
    """Central, immutable result artifact of drift verify."""

    schema_: str = Field(default="evidence-package-v1", alias="schema")
    version: str
    change_set_id: str
    repo: str
    verified_at: datetime
    drift_score: float
    spec_confidence_score: float
    action_recommendation: ActionRecommendation
    violations: list[ViolationFinding] = Field(default_factory=list)
    functional_evidence: FunctionalEvidence = Field(
        default_factory=FunctionalEvidence
    )
    independent_review: IndependentReviewResult | None = None
    rule_promotions: list[RulePromotionProposal] = Field(default_factory=list)
    flags: frozenset[EvidenceFlag] = Field(default_factory=frozenset)

    model_config = {"populate_by_name": True}

    @field_validator("drift_score", "spec_confidence_score")
    @classmethod
    def score_in_range(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Score must be in [0.0, 1.0], got {v}")
        return v

    @model_validator(mode="after")
    def no_changes_invariants(self) -> EvidencePackage:
        if EvidenceFlag.no_changes_detected in self.flags:
            if self.violations:
                raise ValueError(
                    "no_changes_detected flag requires empty violations list"
                )
            if self.drift_score != 0.0:
                raise ValueError(
                    "no_changes_detected flag requires drift_score == 0.0"
                )
            if self.spec_confidence_score != 1.0:
                raise ValueError(
                    "no_changes_detected flag requires spec_confidence_score == 1.0"
                )
        return self


def compute_change_set_id(diff_text: str) -> str:
    """Return sha256 hex digest of diff_text, or 'empty' for blank diffs."""
    stripped = diff_text.strip()
    if not stripped:
        return "empty"
    return hashlib.sha256(stripped.encode()).hexdigest()
