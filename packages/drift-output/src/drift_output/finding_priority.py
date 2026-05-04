"""Dependency-light finding prioritization and recommendation helpers.

These helpers are shared across API and output surfaces to avoid import
cycles between serialization layers.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from drift_sdk.models import Finding, Severity, SignalType

from drift_output.recommendations import generate_recommendation

if TYPE_CHECKING:
    from drift_sdk.models import FileHistory

_ARCHITECTURE_BOUNDARY_SIGNALS = {
    SignalType.ARCHITECTURE_VIOLATION,
    SignalType.CIRCULAR_IMPORT,
    SignalType.CO_CHANGE_COUPLING,
    SignalType.COHESION_DEFICIT,
    SignalType.FAN_OUT_EXPLOSION,
}

_STYLE_OR_HYGIENE_SIGNALS = {
    SignalType.NAMING_CONTRACT_VIOLATION,
    SignalType.DOC_IMPL_DRIFT,
    SignalType.EXPLAINABILITY_DEFICIT,
    SignalType.BROAD_EXCEPTION_MONOCULTURE,
    SignalType.GUARD_CLAUSE_DEFICIT,
    SignalType.DEAD_CODE_ACCUMULATION,
}

_SEVERITY_RANK = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}

_CONTEXT_WEIGHTS_CACHE: tuple[float, float, float] | None = None


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_context_score_weights() -> tuple[float, float, float]:
    """Load learned context weights from JSON file when available.

    Expected format:
    {"churn": 0.5, "ownership": 0.3, "recency": 0.2}
    """
    global _CONTEXT_WEIGHTS_CACHE
    if _CONTEXT_WEIGHTS_CACHE is not None:
        return _CONTEXT_WEIGHTS_CACHE

    default = (0.5, 0.3, 0.2)
    path = os.getenv("DRIFT_CONTEXT_WEIGHTS_PATH")
    if not path:
        _CONTEXT_WEIGHTS_CACHE = default
        return _CONTEXT_WEIGHTS_CACHE

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        churn = max(0.0, float(payload.get("churn", default[0])))
        ownership = max(0.0, float(payload.get("ownership", default[1])))
        recency = max(0.0, float(payload.get("recency", default[2])))
        total = churn + ownership + recency
        if total <= 1e-9:
            _CONTEXT_WEIGHTS_CACHE = default
        else:
            _CONTEXT_WEIGHTS_CACHE = (
                churn / total,
                ownership / total,
                recency / total,
            )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        _CONTEXT_WEIGHTS_CACHE = default
    return _CONTEXT_WEIGHTS_CACHE


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _title_simhash64(text: str) -> int:
    tokens = [t for t in re.split(r"[^a-z0-9]+", _normalize_text(text)) if t]
    if not tokens:
        return 0
    weights = [0] * 64
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        value = int.from_bytes(digest[:8], "big", signed=False)
        for bit in range(64):
            if value & (1 << bit):
                weights[bit] += 1
            else:
                weights[bit] -= 1
    output = 0
    for bit, weight in enumerate(weights):
        if weight >= 0:
            output |= 1 << bit
    return output


def _hamming_distance64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _is_near_duplicate(candidate: Finding, existing: Finding) -> bool:
    if _finding_dedupe_key(candidate) == _finding_dedupe_key(existing):
        return True

    if candidate.file_path is None or existing.file_path is None:
        return False
    if candidate.file_path.as_posix() != existing.file_path.as_posix():
        return False

    candidate_rule = candidate.rule_id or str(candidate.signal_type)
    existing_rule = existing.rule_id or str(existing.signal_type)
    if candidate_rule != existing_rule:
        return False

    c_start = int(candidate.start_line or 0)
    e_start = int(existing.start_line or 0)
    if abs(c_start - e_start) > 3:
        return False

    return (
        _hamming_distance64(
            _title_simhash64(candidate.title or ""),
            _title_simhash64(existing.title or ""),
        )
        <= 3
    )


def _dedupe_findings(ranked_findings: list[Finding]) -> tuple[list[Finding], dict[int, int]]:
    """Return canonical findings and duplicate counts keyed by canonical object id."""
    deduped: list[Finding] = []
    seen: dict[tuple[str, str, int, int, str], Finding] = {}
    duplicate_counts: dict[int, int] = {}
    near_dedupe_enabled = _is_truthy(os.getenv("DRIFT_NEAR_DEDUPE", "1"))
    lsh_buckets: dict[tuple[str, str, int], list[Finding]] = {}

    for finding in ranked_findings:
        key = _finding_dedupe_key(finding)
        existing = seen.get(key)
        if existing is None:
            canonical = finding
            if near_dedupe_enabled and finding.file_path is not None:
                file_key = finding.file_path.as_posix()
                rule_key = finding.rule_id or str(finding.signal_type)
                fingerprint = _title_simhash64(finding.title or "")
                bands = (
                    (fingerprint >> 0) & 0xFFFF,
                    (fingerprint >> 16) & 0xFFFF,
                    (fingerprint >> 32) & 0xFFFF,
                    (fingerprint >> 48) & 0xFFFF,
                )
                for band in bands:
                    for candidate in lsh_buckets.get((rule_key, file_key, band), []):
                        if _is_near_duplicate(finding, candidate):
                            canonical = candidate
                            break
                    if canonical is not finding:
                        break
                if canonical is finding:
                    for band in bands:
                        lsh_buckets.setdefault((rule_key, file_key, band), []).append(finding)

            if canonical is finding:
                seen[key] = finding
                deduped.append(finding)
                duplicate_counts[id(finding)] = 1
                continue
            duplicate_counts[id(canonical)] = duplicate_counts.get(id(canonical), 1) + 1
            continue

        duplicate_counts[id(existing)] = duplicate_counts.get(id(existing), 1) + 1

    return deduped, duplicate_counts


def _finding_dedupe_key(f: Finding) -> tuple[str, str, int, int, str]:
    file_path = f.file_path.as_posix() if f.file_path else ""
    start_line = int(f.start_line or 0)
    end_line = int(f.end_line or 0)
    title = (f.title or "").strip().lower()
    rule_id = f.rule_id or f.signal_type
    return (rule_id, file_path, start_line, end_line, title)


def _priority_class(f: Finding) -> str:
    """Map finding to a decision-priority class."""
    if f.signal_type in _ARCHITECTURE_BOUNDARY_SIGNALS:
        return "architecture_boundary"
    if f.signal_type in _STYLE_OR_HYGIENE_SIGNALS:
        return "style_or_hygiene"
    return "structural_risk"


def _priority_rank(priority_class: str) -> int:
    if priority_class == "architecture_boundary":
        return 0
    if priority_class == "structural_risk":
        return 1
    return 2


def _next_step_for_finding(
    f: Finding,
    include_recommendation: bool = False,
) -> str | None:
    if include_recommendation:
        rec = generate_recommendation(f)
        if rec:
            return rec.title
    return f.fix


def _expected_benefit_for_finding(f: Finding) -> str:
    rec = generate_recommendation(f)
    if rec and rec.impact:
        return rec.impact
    if f.severity in (Severity.CRITICAL, Severity.HIGH):
        return "high"
    if f.severity == Severity.MEDIUM:
        return "medium"
    return "low"


def _context_score(
    finding: Finding,
    file_history: FileHistory | None,
) -> float:
    """Return an operational-context urgency score in [0.0, 1.0].

    A higher score indicates a finding in a hotter, more actively modified,
    or more broadly owned file — making it more operationally urgent. The
    score is used as a *secondary* sort key after structural class and
    severity so it only breaks ties, preserving backwards-compatible
    class-label ordering.

    Inputs (all from ``FileHistory``):

    * ``change_frequency_30d`` — weekly change rate over the last 30 days;
      normalised at 2.0 changes/week (weight 50 %).
    * ``unique_authors`` — count of distinct authors; normalised at 5
      authors (weight 30 %).
    * ``last_modified`` — days since last commit to the file; normalised
      at 365 days (weight 20 %, higher recency → higher score).

    When *file_history* is ``None`` or a field is missing, the component
    defaults to 0.0, which leaves existing sort order unchanged.
    """
    if file_history is None:
        return 0.0

    churn = getattr(file_history, "change_frequency_30d", 0.0) or 0.0
    authors = getattr(file_history, "unique_authors", 0) or 0
    last_modified: datetime.datetime | None = getattr(file_history, "last_modified", None)

    churn_score = min(1.0, churn / 2.0)
    ownership_score = min(1.0, authors / 5.0)

    if last_modified is not None:
        now = datetime.datetime.now(tz=datetime.UTC)
        if last_modified.tzinfo is None:
            last_modified = last_modified.replace(tzinfo=datetime.UTC)
        days_since = max(0.0, (now - last_modified).total_seconds() / 86400.0)
        recency_score = max(0.0, 1.0 - days_since / 365.0)
    else:
        recency_score = 0.0

    w_churn, w_ownership, w_recency = _load_context_score_weights()
    return w_churn * churn_score + w_ownership * ownership_score + w_recency * recency_score


def _composite_sort_key(
    finding: Finding,
    file_history: FileHistory | None = None,
    file_histories: dict[str, Any] | None = None,
) -> tuple:
    """Return a sort key that combines structural class, severity, and operational context.

    Pass *file_history* directly, or provide the full *file_histories* mapping
    by file path and let this function resolve the right entry.  When both are
    ``None``, the key degrades gracefully to the legacy ``(_priority_rank,
    _SEVERITY_RANK, -impact)`` ordering.
    """
    if file_history is None and file_histories is not None and finding.file_path is not None:
        file_history = file_histories.get(finding.file_path.as_posix())

    pclass = _priority_class(finding)
    ctx = _context_score(finding, file_history)

    # Use the string .value to stay robust against fake/duck-typed severity objects.
    severity_str = getattr(finding.severity, "value", str(finding.severity)).lower()
    _srank_str = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    srank = _srank_str.get(severity_str, 4)

    return (
        _priority_rank(pclass),
        srank,
        round(-ctx, 6),
        -float(finding.impact),
    )
