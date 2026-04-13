"""Outcome tracking for drift findings across analysis runs.

Records when findings are first detected and when they disappear,
enabling measurement of fix speed and downstream recommendation quality.
All data is stored locally in JSONL format — no network, no LLM.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from drift.models import Finding, FindingStatus


@dataclass
class Outcome:
    """Tracked lifecycle of a single finding across analysis runs."""

    fingerprint: str
    signal_type: str
    recommendation_title: str
    reported_at: str  # ISO-8601
    resolved_at: str | None = None  # ISO-8601 or None
    days_to_fix: float | None = None
    effort_estimate: str = "medium"  # "low" | "medium" | "high"
    was_suppressed: bool = False


def compute_fingerprint(finding: Finding) -> str:
    """Compute a stable SHA-256 fingerprint for a finding.

    Uses ``LogicalLocation.fully_qualified_name`` when available (stable
    across line-number shifts), otherwise falls back to file path + start
    line.  The signal type is always part of the hash so that different
    signals on the same location produce distinct fingerprints.
    """
    if finding.logical_location and finding.logical_location.fully_qualified_name:
        key = f"{finding.signal_type}:{finding.logical_location.fully_qualified_name}"
    elif finding.file_path is not None:
        key = f"{finding.signal_type}:{finding.file_path.as_posix()}:{finding.start_line or 0}"
    else:
        key = f"{finding.signal_type}:{finding.title}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class OutcomeTracker:
    """Persists finding outcomes in a repo-local JSONL file.

    Parameters
    ----------
    outcomes_path:
        Path to the JSONL file (typically ``.drift/outcomes.jsonl``).
    """

    def __init__(self, outcomes_path: Path) -> None:
        self._path = outcomes_path
        self._session_fingerprints: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record(self, finding: Finding, effort_estimate: str = "medium") -> None:
        """Record a finding observed in the current analysis run.

        Idempotent within a single session — repeated calls for the same
        fingerprint are silently ignored (F-06).
        """
        fp = compute_fingerprint(finding)
        if fp in self._session_fingerprints:
            return
        self._session_fingerprints.add(fp)

        # Check whether this fingerprint already has an *active* entry.
        existing = self.load()
        for outcome in existing:
            if outcome.fingerprint == fp and outcome.resolved_at is None:
                return  # still tracked, nothing to do

        outcome = Outcome(
            fingerprint=fp,
            signal_type=finding.signal_type,
            recommendation_title=finding.title,
            reported_at=datetime.now(UTC).isoformat(),
            was_suppressed=finding.status == FindingStatus.SUPPRESSED,
            effort_estimate=effort_estimate,
        )
        self._append(outcome)

    def resolve(self, current_fingerprints: set[str]) -> list[Outcome]:
        """Mark findings that are no longer present as resolved.

        Returns the list of newly resolved outcomes.
        """
        outcomes = self.load()
        now = datetime.now(UTC)
        resolved: list[Outcome] = []

        for outcome in outcomes:
            if outcome.resolved_at is not None:
                continue
            if outcome.fingerprint not in current_fingerprints:
                outcome.resolved_at = now.isoformat()
                reported = datetime.fromisoformat(outcome.reported_at)
                outcome.days_to_fix = (now - reported).total_seconds() / 86400.0
                resolved.append(outcome)

        if resolved:
            self._rewrite(outcomes)

        return resolved

    def load(self) -> list[Outcome]:
        """Load all outcomes from the JSONL file.

        Returns an empty list when the file does not exist (F-05).
        """
        if not self._path.exists():
            return []

        outcomes: list[Outcome] = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                outcomes.append(Outcome(**data))
            except (json.JSONDecodeError, TypeError):
                continue  # skip corrupted lines
        return outcomes

    def archive(self, max_age_days: int = 180) -> int:
        """Move outcomes older than *max_age_days* to an archive file.

        Returns the number of archived entries.
        """
        outcomes = self.load()
        now = datetime.now(UTC)
        keep: list[Outcome] = []
        archived: list[Outcome] = []

        for outcome in outcomes:
            reported = datetime.fromisoformat(outcome.reported_at)
            age_days = (now - reported).total_seconds() / 86400.0
            if age_days > max_age_days and outcome.resolved_at is not None:
                archived.append(outcome)
            else:
                keep.append(outcome)

        if not archived:
            return 0

        # Append to archive file
        archive_path = self._path.with_suffix(".archive.jsonl")
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with archive_path.open("a", encoding="utf-8") as f:
            for outcome in archived:
                f.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")

        # Rewrite active file
        self._rewrite(keep)
        return len(archived)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, outcome: Outcome) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")

    def _rewrite(self, outcomes: list[Outcome]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            for outcome in outcomes:
                f.write(json.dumps(asdict(outcome), ensure_ascii=False) + "\n")
