#!/usr/bin/env python3
"""Ablation study: MDS similarity_threshold sensitivity.

Runs the MDS signal at different similarity thresholds (0.70–0.95)
against the ground-truth fixtures and measures Precision/Recall/F1.

Usage:
    python scripts/ablation_mds_threshold.py
"""

from __future__ import annotations

import datetime
import json
import sys
import tempfile
from pathlib import Path

# Ensure src is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tests.fixtures.ground_truth import ALL_FIXTURES, GroundTruthFixture  # noqa: E402

from drift.config import DriftConfig, ThresholdsConfig  # noqa: E402
from drift.ingestion.ast_parser import parse_file  # noqa: E402
from drift.ingestion.file_discovery import discover_files  # noqa: E402
from drift.models import FileHistory, Finding, ParseResult, SignalType  # noqa: E402
from drift.signals.base import AnalysisContext, create_signals  # noqa: E402


def _run_mds_at_threshold(
    fixtures: list[GroundTruthFixture],
    threshold: float,
    base_dir: Path,
) -> dict[str, int]:
    """Run MDS signal at a given threshold and compute TP/FP/FN."""
    tp = fp = fn = tn = 0

    mds_fixtures = [
        f for f in fixtures if any(e.signal_type == SignalType.MUTANT_DUPLICATE for e in f.expected)
    ]

    for fixture in mds_fixtures:
        fixture_dir = fixture.materialize(base_dir / f"t{threshold:.2f}" / fixture.name)

        config = DriftConfig(
            include=["**/*.py"],
            exclude=["**/__pycache__/**"],
            embeddings_enabled=False,
            thresholds=ThresholdsConfig(similarity_threshold=threshold),
        )

        files = discover_files(fixture_dir, config.include, config.exclude)
        parse_results: list[ParseResult] = []
        for finfo in files:
            pr = parse_file(finfo.path, fixture_dir, finfo.language)
            parse_results.append(pr)

        file_histories: dict[str, FileHistory] = {}
        for finfo in files:
            key = finfo.path.as_posix()
            file_histories[key] = FileHistory(
                path=finfo.path,
                total_commits=10,
                unique_authors=1,
                last_modified=datetime.datetime.now(tz=datetime.UTC),
                first_seen=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=120),
            )

        ctx = AnalysisContext(
            repo_path=fixture_dir,
            config=config,
            parse_results=parse_results,
            file_histories=file_histories,
            embedding_service=None,
        )

        signals = [s for s in create_signals(ctx) if s.signal_type == SignalType.MUTANT_DUPLICATE]

        all_findings: list[Finding] = []
        for signal in signals:
            all_findings.extend(signal.analyze(parse_results, file_histories, config))

        for exp in fixture.expected:
            if exp.signal_type != SignalType.MUTANT_DUPLICATE:
                continue
            detected = any(f.signal_type == SignalType.MUTANT_DUPLICATE for f in all_findings)
            if exp.should_detect and detected:
                tp += 1
            elif exp.should_detect and not detected:
                fn += 1
            elif not exp.should_detect and detected:
                fp += 1
            else:
                tn += 1

    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def main() -> None:
    thresholds = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

    print("=" * 70)
    print("MDS Similarity Threshold Ablation Study")
    print("=" * 70)
    header = (
        f"\n{'Threshold':>10s} {'TP':>5s} {'FP':>5s} {'FN':>5s}"
        f" {'Precision':>10s} {'Recall':>8s} {'F1':>8s}"
    )
    print(header)
    print("-" * 60)

    results = []

    with tempfile.TemporaryDirectory(prefix="drift_mds_ablation_") as tmpdir:
        base_dir = Path(tmpdir)

        for threshold in thresholds:
            counts = _run_mds_at_threshold(ALL_FIXTURES, threshold, base_dir)
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]

            precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

            print(
                f"{threshold:>10.2f} {tp:>5d} {fp:>5d} {fn:>5d}"
                f" {precision:>10.2%} {recall:>8.2%} {f1:>8.2%}"
            )

            results.append({
                "threshold": threshold,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
            })

    print("-" * 55)

    # Find optimal threshold (max F1)
    best = max(results, key=lambda r: r["f1"])
    print(f"\nOptimal threshold: {best['threshold']:.2f} (F1={best['f1']:.2%})")

    # Save results
    output_path = Path("benchmark_results") / "mds_threshold_ablation.json"
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    main()
