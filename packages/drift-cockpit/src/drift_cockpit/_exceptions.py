"""Domain exceptions for drift-cockpit (Feature 006)."""

from __future__ import annotations


class MissingEvidenceError(ValueError):
    """Raised when build_decision_bundle() receives no signal findings."""

    def __init__(self, pr_id: str) -> None:
        super().__init__(
            f"No signal findings provided for PR '{pr_id}'. "
            "Decision status cannot be computed without evidence; "
            "status defaults to no_go."
        )
        self.pr_id = pr_id


class VersionConflictError(RuntimeError):
    """Raised when a LedgerEntry write is attempted with a stale version."""

    def __init__(self, pr_id: str, expected: int, actual: int) -> None:
        super().__init__(
            f"Version conflict for PR '{pr_id}': "
            f"expected version {expected}, found {actual}. "
            "Fetch the latest entry and retry."
        )
        self.pr_id = pr_id
        self.expected = expected
        self.actual = actual


class MissingOverrideJustificationError(ValueError):
    """Raised when a human override has no justification."""

    def __init__(self, pr_id: str) -> None:
        super().__init__(
            f"PR '{pr_id}': human decision differs from recommendation "
            "but no override_reason was provided. "
            "Override justification is mandatory (FR-013)."
        )
        self.pr_id = pr_id
