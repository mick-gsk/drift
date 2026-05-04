"""Rule promotion — detects recurring violation patterns and proposes new rules."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from drift_verify._models import (
    PatternHistoryEntry,
    RulePromotionProposal,
    ViolationFinding,
)

_log = logging.getLogger(__name__)

_DEFAULT_HISTORY_PATH = Path(".drift") / "pattern_history.jsonl"


def _make_pattern_key(violation: ViolationFinding) -> str:
    file_pattern = violation.file or "*"
    return f"{violation.violation_type.value}::{file_pattern}"


class PatternHistoryStore:
    """Append-only JSONL store for violation pattern history."""

    def __init__(self, path: Path = _DEFAULT_HISTORY_PATH) -> None:
        self._path = path

    def append(self, entry: PatternHistoryEntry) -> None:
        """Append one entry; creates .drift/ directory if missing."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.model_dump()) + "\n")

    def load(self) -> list[PatternHistoryEntry]:
        """Load all entries from JSONL; returns empty list if file missing."""
        if not self._path.exists():
            return []
        entries: list[PatternHistoryEntry] = []
        try:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    entries.append(PatternHistoryEntry.model_validate_json(line))
        except Exception as exc:  # noqa: BLE001
            _log.warning("Failed to load pattern history: %s", exc)
        return entries


def compute_promotions(
    history: list[PatternHistoryEntry],
    violations: list[ViolationFinding],
    threshold: int = 5,
) -> list[RulePromotionProposal]:
    """Pure function: compute rule promotion proposals from history + new violations.

    Returns a proposal for each pattern_key that meets/exceeds `threshold`.
    """
    # Count occurrences per pattern key from history
    counts: dict[str, list[PatternHistoryEntry]] = {}
    for entry in history:
        key = f"{entry.type}::{entry.pattern}"
        counts.setdefault(key, []).append(entry)

    # Count new violations in this run (not yet persisted)
    new_files: dict[str, list[str]] = {}
    for v in violations:
        key = _make_pattern_key(v)
        new_files.setdefault(key, []).append(v.file or "*")

    proposals: list[RulePromotionProposal] = []
    all_keys = set(counts) | set(new_files)
    for key in all_keys:
        existing = len(counts.get(key, []))
        new_count = len(new_files.get(key, []))
        total = existing + new_count
        if total >= threshold:
            parts = key.split("::", 1)
            vtype = parts[0]
            pattern = parts[1] if len(parts) > 1 else "*"
            all_files = [e.file for e in counts.get(key, [])] + new_files.get(key, [])
            proposals.append(
                RulePromotionProposal(
                    pattern_key=key,
                    occurrence_count=total,
                    threshold=threshold,
                    suggested_rule_id=f"auto_{vtype}_{pattern.replace('/', '_')[:20]}",
                    suggested_description=(
                        f"Auto-detected recurring {vtype} in '{pattern}' "
                        f"({total} occurrences)"
                    ),
                    affected_files=list(dict.fromkeys(all_files)),
                )
            )

    return proposals


def record_violations(
    violations: list[ViolationFinding],
    store: PatternHistoryStore,
) -> None:
    """Append new history entries for current violations."""
    ts = datetime.now(tz=UTC).isoformat()
    for v in violations:
        store.append(
            PatternHistoryEntry(
                type=v.violation_type.value,
                pattern=v.file or "*",
                file=v.file or "*",
                ts=ts,
            )
        )
