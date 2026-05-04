"""drift-verify: evidence-based drift verification for drift-analyzer.

Public API:
    verify(change_set, *, reviewer=None, functional_evidence=None, ...) -> EvidencePackage
"""

from drift_verify._cmd import evidence_cmd
from drift_verify._models import (
    ActionRecommendation,
    ChangeSet,
    EvidenceFlag,
    EvidencePackage,
    FunctionalEvidence,
    IndependentReviewResult,
    PatternHistoryEntry,
    RulePromotionProposal,
    Severity,
    Verdict,
    ViolationFinding,
    ViolationType,
)
from drift_verify._reviewer import MockReviewerAgent, ReviewerAgentProtocol
from drift_verify._verify import verify

__all__ = [
    "ActionRecommendation",
    "ChangeSet",
    "EvidenceFlag",
    "EvidencePackage",
    "FunctionalEvidence",
    "IndependentReviewResult",
    "MockReviewerAgent",
    "PatternHistoryEntry",
    "ReviewerAgentProtocol",
    "RulePromotionProposal",
    "Severity",
    "Verdict",
    "ViolationFinding",
    "ViolationType",
    "evidence_cmd",
    "verify",
]
