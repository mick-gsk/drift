"""External-ground-truth Defect Corpus recall tests.

Runs each :class:`DefectCorpusEntry` through the drift signal engine and
asserts recall — i.e., that drift *would have detected* the known bug pattern
before a fix was merged.

Key differences from ``test_precision_recall.py``
--------------------------------------------------
* **Recall-only.**  We only assert ``should_detect=True`` expectations.
  The corpus does not make precision claims; it answers "could drift catch
  this class of confirmed real bug?"
* **Provenance metadata in failure messages.**  When a fixture fails, the
  assertion message includes the ``evidence_url`` and ``bug_summary`` so it
  is immediately clear which real bug is not being detected.
* **Separate marker.**  Use ``pytest -m defect_corpus`` to run only this suite.

Usage
-----
    pytest tests/test_defect_corpus.py -v --tb=short
    pytest -m defect_corpus -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from drift.precision import (
    ensure_signals_registered,
    has_matching_finding,
    run_fixture,
)
from tests.fixtures.defect_corpus import (
    ALL_DEFECT_CORPUS,
    DefectCorpusEntry,
)

ensure_signals_registered()


# ── Per-entry recall test ─────────────────────────────────────────────────────


@pytest.mark.defect_corpus
@pytest.mark.parametrize(
    "entry",
    ALL_DEFECT_CORPUS,
    ids=[e.fixture.name for e in ALL_DEFECT_CORPUS],
)
def test_defect_corpus_recall(
    entry: DefectCorpusEntry,
    tmp_path: Path,
) -> None:
    """Assert that drift detects each known bad pattern (recall check).

    A failure means drift would *not* have caught this confirmed bug class
    before the fix was merged.  The evidence_url in the failure message links
    to the source that confirmed the bug as real.
    """
    relevant_signals = {e.signal_type for e in entry.fixture.expected}
    findings, _warnings = run_fixture(
        entry.fixture, tmp_path, signal_filter=relevant_signals
    )

    for exp in entry.fixture.expected:
        if not exp.should_detect:
            continue  # corpus is recall-only — skip TN expectations

        detected = has_matching_finding(findings, exp)
        assert detected, (
            f"[FN — recall failure] {entry.fixture.name}\n"
            f"  Signal    : {exp.signal_type}\n"
            f"  File      : {exp.file_path}\n"
            f"  Bug       : {entry.bug_summary}\n"
            f"  Source    : {entry.evidence_url}\n"
            f"  Pre-fix   : {entry.pre_fix_note}\n"
            f"  Findings  : {[(f.signal_type, str(f.file_path)) for f in findings]}"
        )


# ── Aggregate recall report ───────────────────────────────────────────────────


@pytest.mark.defect_corpus
def test_defect_corpus_recall_report(tmp_path: Path) -> None:
    """Print an aggregate recall report across all corpus entries.

    Minimum quality bar: overall recall must be >= 0.70 (5 out of 7 entries
    must be detected).  This threshold intentionally leaves room for cases
    where a confirmed bug class has no current drift signal, while still
    preventing silent degradation.
    """
    from collections import defaultdict

    by_signal: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "detected": 0})
    by_class: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "detected": 0})

    total = 0
    detected_count = 0

    for entry in ALL_DEFECT_CORPUS:
        relevant_signals = {e.signal_type for e in entry.fixture.expected}
        findings, _ = run_fixture(entry.fixture, tmp_path, signal_filter=relevant_signals)

        for exp in entry.fixture.expected:
            if not exp.should_detect:
                continue
            total += 1
            sig_key = exp.signal_type.value
            cls_key = entry.bug_class.value
            by_signal[sig_key]["total"] += 1
            by_class[cls_key]["total"] += 1

            if has_matching_finding(findings, exp):
                detected_count += 1
                by_signal[sig_key]["detected"] += 1
                by_class[cls_key]["detected"] += 1

    recall = detected_count / total if total > 0 else 0.0

    # Build report string
    lines = [
        "",
        "Defect Corpus Recall Report (External Ground Truth)",
        "=" * 60,
        f"  Overall recall: {detected_count}/{total} = {recall:.2%}",
        "",
        "  By signal:",
    ]
    for sig, counts in sorted(by_signal.items()):
        r = counts["detected"] / counts["total"] if counts["total"] > 0 else 0.0
        lines.append(
            f"    {sig:<35s}  {counts['detected']}/{counts['total']}  ({r:.0%})"
        )
    lines.append("")
    lines.append("  By bug class:")
    for cls, counts in sorted(by_class.items()):
        r = counts["detected"] / counts["total"] if counts["total"] > 0 else 0.0
        lines.append(
            f"    {cls:<35s}  {counts['detected']}/{counts['total']}  ({r:.0%})"
        )
    lines.append("-" * 60)
    lines.append(f"  Minimum required recall: 0.70 ({int(0.70 * total)}/{total})")

    print("\n".join(lines))

    assert recall >= 0.70, (
        f"Defect corpus recall {recall:.2%} is below the 0.70 minimum gate "
        f"({detected_count}/{total} entries detected).  "
        "A drift signal may have regressed or a new confirmed bug class is not yet covered."
    )
