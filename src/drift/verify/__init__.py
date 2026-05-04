"""Re-export stub — drift_verify (ADR-100 pattern).

All implementation lives in packages/drift-verify/src/drift_verify/.
"""

import importlib as _importlib
import sys as _sys

from drift_verify import (  # noqa: F401
    ActionRecommendation,
    ChangeSet,
    EvidenceFlag,
    EvidencePackage,
    FunctionalEvidence,
    IndependentReviewResult,
    MockReviewerAgent,
    PatternHistoryEntry,
    ReviewerAgentProtocol,
    RulePromotionProposal,
    Severity,
    Verdict,
    ViolationFinding,
    ViolationType,
    verify,
)

_sys.modules[__name__] = _importlib.import_module("drift_verify")
