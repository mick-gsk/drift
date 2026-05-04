"""Append-only Decision Ledger for drift-cockpit (Feature 006).

All I/O is isolated here. Pure helpers in _models.py.
Optimistic locking via version field (FR-015).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from drift_cockpit._exceptions import (
    MissingOverrideJustificationError,
    VersionConflictError,
)
from drift_cockpit._models import (
    LedgerEntry,
    OutcomeSnapshot,
    OutcomeState,
)

_DEFAULT_LEDGER_DIR = Path(".drift") / "cockpit"


def _ledger_path(pr_id: str, base: Path = _DEFAULT_LEDGER_DIR) -> Path:
    return base / f"{pr_id}.jsonl"


def validate_override(entry: LedgerEntry) -> None:
    """Raise MissingOverrideJustificationError if override has no reason (FR-013)."""
    if (
        entry.human_status != entry.recommended_status
        and not entry.override_reason
    ):
        raise MissingOverrideJustificationError(entry.pr_id)


def read_ledger(pr_id: str, *, base: Path = _DEFAULT_LEDGER_DIR) -> list[LedgerEntry]:
    """Read all ledger entries for a PR (FR-006)."""
    path = _ledger_path(pr_id, base)
    if not path.exists():
        return []
    entries: list[LedgerEntry] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(LedgerEntry.model_validate_json(line))
    return entries


def write_ledger_entry(
    entry: LedgerEntry,
    *,
    base: Path = _DEFAULT_LEDGER_DIR,
) -> None:
    """Append a LedgerEntry to the PR's ledger file with optimistic locking (FR-015).

    Raises VersionConflictError if the expected version does not match the last
    stored version for this PR.
    """
    validate_override(entry)

    path = _ledger_path(entry.pr_id, base)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = read_ledger(entry.pr_id, base=base)
    if existing:
        last_version = existing[-1].version
        expected_version = last_version + 1
        if entry.version != expected_version:
            raise VersionConflictError(entry.pr_id, expected_version, entry.version)

    with path.open("a", encoding="utf-8") as fh:
        fh.write(entry.model_dump_json() + "\n")


def update_outcome(
    pr_id: str,
    *,
    window: str,
    state: OutcomeState,
    rework_events: int | None = None,
    merge_velocity_delta: float | None = None,
    base: Path = _DEFAULT_LEDGER_DIR,
) -> LedgerEntry:
    """Append an updated LedgerEntry with the outcome for the given window (FR-007/FR-014).

    Creates a new versioned entry rather than mutating an existing one (append-only).
    """
    existing = read_ledger(pr_id, base=base)
    if not existing:
        raise ValueError(f"No ledger entries found for PR '{pr_id}'.")

    last = existing[-1]
    snapshot = OutcomeSnapshot(
        window=window,
        state=state,
        rework_events=rework_events,
        merge_velocity_delta=merge_velocity_delta,
        captured_at=datetime.utcnow() if state == OutcomeState.captured else None,
    )
    updated_entry = LedgerEntry(
        ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
        pr_id=pr_id,
        recommended_status=last.recommended_status,
        human_status=last.human_status,
        override_reason=last.override_reason,
        decision_actor=last.decision_actor,
        evidence_refs=last.evidence_refs,
        outcome_7d=snapshot if window == "7d" else last.outcome_7d,
        outcome_30d=snapshot if window == "30d" else last.outcome_30d,
        version=last.version + 1,
        created_at=last.created_at,
        updated_at=datetime.utcnow(),
    )
    write_ledger_entry(updated_entry, base=base)
    return updated_entry
