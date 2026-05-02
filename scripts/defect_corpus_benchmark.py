#!/usr/bin/env python3
"""Defect Corpus Recall Benchmark for drift.

Runs the external-ground-truth defect corpus against the current signal engine
and writes a machine-readable recall report to
``benchmark_results/defect_corpus_recall.json``.

Unlike ``tests/test_defect_corpus.py`` (which is a pass/fail gate), this
script produces a JSON artefact that can be committed and compared across
drift versions to track recall regressions.

Usage
-----
    python scripts/defect_corpus_benchmark.py
    python scripts/defect_corpus_benchmark.py --out path/to/output.json
    python scripts/defect_corpus_benchmark.py --verbose

Exit codes
----------
    0  All entries detected (recall = 1.0)
    1  At least one entry not detected (recall < 1.0)
    2  Recall below the 0.70 minimum gate
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))
sys.path.insert(0, str(_REPO_ROOT))

from drift.precision import (  # noqa: E402 (sys.path set above)
    ensure_signals_registered,
    has_matching_finding,
    run_fixture,
)
from tests.fixtures.defect_corpus import (  # noqa: E402
    ALL_DEFECT_CORPUS,
)

_DEFAULT_OUT = _REPO_ROOT / "benchmark_results" / "defect_corpus_recall.json"
_MIN_RECALL = 0.70


def _drift_version() -> str:
    try:
        import importlib.metadata
        return importlib.metadata.version("drift-analyzer")
    except Exception:
        return "unknown"


def run(out_path: Path, verbose: bool = False) -> int:
    """Run the defect corpus and write the results JSON.  Returns exit code."""
    ensure_signals_registered()

    by_signal: dict[str, dict[str, int]] = defaultdict(lambda: {"entries": 0, "detected": 0})
    by_class: dict[str, dict[str, int]] = defaultdict(lambda: {"entries": 0, "detected": 0})
    entry_results: list[dict] = []

    total = 0
    detected_count = 0

    with tempfile.TemporaryDirectory(prefix="drift_defect_corpus_") as tmpdir:
        tmp_path = Path(tmpdir)

        for entry in ALL_DEFECT_CORPUS:
            relevant_signals = {e.signal_type for e in entry.fixture.expected}
            findings, warnings = run_fixture(
                entry.fixture, tmp_path, signal_filter=relevant_signals
            )

            for exp in entry.fixture.expected:
                if not exp.should_detect:
                    continue

                total += 1
                sig_key = exp.signal_type.value
                cls_key = entry.bug_class.value
                by_signal[sig_key]["entries"] += 1
                by_class[cls_key]["entries"] += 1

                detected = has_matching_finding(findings, exp)
                if detected:
                    detected_count += 1
                    by_signal[sig_key]["detected"] += 1
                    by_class[cls_key]["detected"] += 1

                if verbose:
                    status = "DETECTED" if detected else "MISSED"
                    print(
                        f"  [{status}] {entry.fixture.name} / {sig_key} @ {exp.file_path}"
                    )

            entry_results.append(
                {
                    "id": entry.fixture.name,
                    "signal": [
                        e.signal_type.value
                        for e in entry.fixture.expected
                        if e.should_detect
                    ],
                    "bug_class": entry.bug_class.value,
                    "detected": all(
                        has_matching_finding(findings, e)
                        for e in entry.fixture.expected
                        if e.should_detect
                    ),
                    "evidence_url": entry.evidence_url,
                    "bug_summary": entry.bug_summary,
                    "warning_count": len(warnings),
                }
            )

    recall = detected_count / total if total > 0 else 0.0

    by_signal_serialized = {
        sig: {
            "entries": v["entries"],
            "detected": v["detected"],
            "recall": round(v["detected"] / v["entries"], 4) if v["entries"] > 0 else 0.0,
        }
        for sig, v in sorted(by_signal.items())
    }
    by_class_serialized = {
        cls: {
            "entries": v["entries"],
            "detected": v["detected"],
            "recall": round(v["detected"] / v["entries"], 4) if v["entries"] > 0 else 0.0,
        }
        for cls, v in sorted(by_class.items())
    }

    output = {
        "metadata": {
            "generated_at": datetime.now(tz=UTC).isoformat(),
            "drift_version": _drift_version(),
            "methodology": "external_ground_truth_transformative",
            "methodology_note": (
                "Each corpus entry is a transformative reproduction of a confirmed "
                "real-world bug class.  Original-code-verbatim copying is prohibited; "
                "all function names and structures are independently authored."
            ),
            "min_recall_gate": _MIN_RECALL,
        },
        "summary": {
            "total_entries": total,
            "detected": detected_count,
            "recall": round(recall, 4),
            "gate_passed": recall >= _MIN_RECALL,
        },
        "by_signal": by_signal_serialized,
        "by_class": by_class_serialized,
        "entries": entry_results,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")
    print(
        f"Recall: {detected_count}/{total} = {recall:.2%}  "
        f"(gate: {_MIN_RECALL:.0%})  "
        f"{'PASS' if recall >= _MIN_RECALL else 'FAIL'}"
    )

    if recall < _MIN_RECALL:
        return 2
    if recall < 1.0:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the defect corpus recall benchmark and write JSON output."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=_DEFAULT_OUT,
        help=f"Output JSON path (default: {_DEFAULT_OUT})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-entry detection status.",
    )
    args = parser.parse_args()
    sys.exit(run(args.out, verbose=args.verbose))


if __name__ == "__main__":
    main()
