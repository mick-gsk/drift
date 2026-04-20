"""Intent-aware finding matcher.

Maps analysis findings to violated intent requirements by matching
``Finding.signal_type`` against ``Requirement.validation_signal``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from drift.intent.models import IntentContract
from drift.models import Finding


@dataclass
class RequirementStatus:
    """Validation status for a single intent requirement."""

    requirement_id: str
    description_plain: str
    satisfied: bool
    violated_by: list[Finding] = field(default_factory=list)


def match_findings_to_contracts(
    findings: list[Finding],
    contracts: list[IntentContract],
) -> list[RequirementStatus]:
    """Match findings against all requirements from all contracts.

    Parameters
    ----------
    findings:
        Findings from ``drift analyze``.
    contracts:
        Intent contracts loaded from ``.drift-intent.yaml``.

    Returns
    -------
    list[RequirementStatus]
        One entry per requirement across all contracts.
    """
    if not contracts:
        return []

    # Index findings by signal_type for O(1) lookup
    signal_index: dict[str, list[Finding]] = {}
    for f in findings:
        signal_index.setdefault(f.signal_type, []).append(f)

    statuses: list[RequirementStatus] = []
    for contract in contracts:
        for req in contract.requirements:
            if req.validation_signal is None:
                # No signal mapping → always satisfied (manual requirement)
                statuses.append(
                    RequirementStatus(
                        requirement_id=req.id,
                        description_plain=req.description_plain,
                        satisfied=True,
                    )
                )
                continue

            matching = signal_index.get(req.validation_signal, [])
            statuses.append(
                RequirementStatus(
                    requirement_id=req.id,
                    description_plain=req.description_plain,
                    satisfied=len(matching) == 0,
                    violated_by=list(matching),
                )
            )

    return statuses
