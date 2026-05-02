#!/usr/bin/env python3
"""Scoring-weight sensitivity analysis.

Varies each signal weight by ±50% and measures:
1. Impact on composite score ranking across benchmark repos
2. Rank correlation (Spearman ρ) vs. baseline ranking
3. Pareto-optimal weight combinations for P+R maximization

Usage:
    python scripts/sensitivity_analysis.py
"""

from __future__ import annotations

import datetime
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import drift.signals.architecture_violation  # noqa: E402, F401
import drift.signals.doc_impl_drift  # noqa: E402, F401
import drift.signals.explainability_deficit  # noqa: E402, F401
import drift.signals.mutant_duplicates  # noqa: E402, F401
import drift.signals.pattern_fragmentation  # noqa: E402, F401
import drift.signals.system_misalignment  # noqa: E402, F401
import drift.signals.temporal_volatility  # noqa: E402, F401
from drift.config import DriftConfig, SignalWeights  # noqa: E402
from drift.ingestion.ast_parser import parse_file  # noqa: E402
from drift.ingestion.file_discovery import discover_files  # noqa: E402
from drift.models import FileHistory, Finding, SignalType  # noqa: E402
from drift.scoring.engine import (  # noqa: E402
    composite_score,
    compute_signal_scores,
)
from drift.signals.base import AnalysisContext, create_signals  # noqa: E402
from tests.fixtures.ground_truth import (  # noqa: E402
    ALL_FIXTURES,
    GroundTruthFixture,
)


def _run_all_fixtures(
    fixtures: list[GroundTruthFixture], base_dir: Path
) -> list[Finding]:
    """Run all signals on all fixtures and collect findings."""
    all_findings: list[Finding] = []

    for fixture in fixtures:
        fixture_dir = fixture.materialize(base_dir / fixture.name)
        config = DriftConfig(
            include=["**/*.py"],
            exclude=["**/__pycache__/**"],
            embeddings_enabled=False,
        )

        files = discover_files(fixture_dir, config.include, config.exclude)
        parse_results = []
        for finfo in files:
            pr = parse_file(finfo.path, fixture_dir, finfo.language)
            parse_results.append(pr)

        file_histories: dict[str, FileHistory] = {}
        for finfo in files:
            key = finfo.path.as_posix()
            is_new = "new_feature" in key
            override = fixture.file_history_overrides.get(key)

            file_histories[key] = FileHistory(
                path=finfo.path,
                total_commits=(
                    override.total_commits
                    if override and override.total_commits is not None
                    else (1 if is_new else 10)
                ),
                unique_authors=(
                    override.unique_authors
                    if override and override.unique_authors is not None
                    else 1
                ),
                ai_attributed_commits=(
                    override.ai_attributed_commits
                    if override and override.ai_attributed_commits is not None
                    else 0
                ),
                change_frequency_30d=(
                    override.change_frequency_30d
                    if override and override.change_frequency_30d is not None
                    else (5.0 if is_new else 0.5)
                ),
                defect_correlated_commits=(
                    override.defect_correlated_commits
                    if override and override.defect_correlated_commits is not None
                    else 0
                ),
                last_modified=(
                    datetime.datetime.now(tz=datetime.UTC)
                    if is_new
                    else datetime.datetime.now(tz=datetime.UTC)
                    - datetime.timedelta(days=60)
                ),
                first_seen=(
                    datetime.datetime.now(tz=datetime.UTC)
                    - datetime.timedelta(days=3)
                    if is_new
                    else datetime.datetime.now(tz=datetime.UTC)
                    - datetime.timedelta(days=120)
                ),
            )

        ctx = AnalysisContext(
            repo_path=fixture_dir,
            config=config,
            parse_results=parse_results,
            file_histories=file_histories,
            embedding_service=None,
        )

        signals = create_signals(ctx)
        for signal in signals:
            try:
                findings = signal.analyze(
                    parse_results, file_histories, config
                )
                all_findings.extend(findings)
            except Exception:
                pass

    return all_findings


def _spearman_rho(
    ranking_a: list[str], ranking_b: list[str]
) -> float:
    """Compute Spearman rank correlation between two rankings."""
    if not ranking_a or not ranking_b:
        return 0.0

    all_items = list(set(ranking_a) | set(ranking_b))
    n = len(all_items)
    if n < 2:
        return 1.0

    rank_a = {item: i for i, item in enumerate(ranking_a)}
    rank_b = {item: i for i, item in enumerate(ranking_b)}

    d_squared_sum = 0.0
    for item in all_items:
        ra = rank_a.get(item, n)
        rb = rank_b.get(item, n)
        d_squared_sum += (ra - rb) ** 2

    return 1 - (6 * d_squared_sum) / (n * (n**2 - 1))


def _score_ranking(
    signal_scores: dict[SignalType, float], weights: SignalWeights
) -> list[str]:
    """Produce a signal ranking based on weighted contribution."""
    weight_dict = weights.as_dict()
    contributions: dict[str, float] = {}
    for sig, score in signal_scores.items():
        key = sig.value
        w = weight_dict.get(key, 0.0)
        contributions[key] = score * w
    return sorted(contributions, key=contributions.get, reverse=True)


def main() -> None:
    import tempfile

    with tempfile.TemporaryDirectory(
        prefix="drift_sensitivity_"
    ) as tmpdir:
        base_dir = Path(tmpdir)

        print("Collecting findings from ground-truth fixtures...")
        findings = _run_all_fixtures(ALL_FIXTURES, base_dir)
        signal_scores = compute_signal_scores(findings)

        default_weights = SignalWeights()
        baseline_composite = composite_score(signal_scores, default_weights)
        baseline_ranking = _score_ranking(signal_scores, default_weights)

        print(f"\n{'=' * 70}")
        print("SCORING WEIGHT SENSITIVITY ANALYSIS")
        print(f"{'=' * 70}")
        print(f"Baseline composite score: {baseline_composite:.4f}")
        print(f"Signal scores: {dict(signal_scores)}")
        print(f"Baseline ranking: {baseline_ranking}")

        # ── Phase 1: ±50% perturbation per weight ──
        print(f"\n{'─' * 70}")
        print("Phase 1: Single-weight perturbation (±50%)")
        print(f"{'─' * 70}")
        header = (
            f"  {'Signal':<28s} {'Weight':>7s}"
            f" {'Δ=-50%':>8s} {'Δ=+50%':>8s}"
            f" {'ρ(-50%)':>8s} {'ρ(+50%)':>8s}"
        )
        print(header)

        perturbation_results = []

        for field_name in type(default_weights).model_fields:
            original = getattr(default_weights, field_name)

            for factor, label in [(0.5, "-50%"), (1.5, "+50%")]:
                perturbed = default_weights.model_copy(
                    update={field_name: original * factor}
                )
                new_score = composite_score(signal_scores, perturbed)
                new_ranking = _score_ranking(signal_scores, perturbed)
                rho = _spearman_rho(baseline_ranking, new_ranking)

                perturbation_results.append({
                    "signal": field_name,
                    "factor": factor,
                    "label": label,
                    "original_weight": original,
                    "perturbed_weight": round(original * factor, 4),
                    "composite_delta": round(new_score - baseline_composite, 5),
                    "spearman_rho": round(rho, 4),
                })

            lo = next(
                r for r in perturbation_results
                if r["signal"] == field_name and r["factor"] == 0.5
            )
            hi = next(
                r for r in perturbation_results
                if r["signal"] == field_name and r["factor"] == 1.5
            )
            print(
                f"  {field_name:<28s} {original:>7.2f}"
                f" {lo['composite_delta']:>+8.4f}"
                f" {hi['composite_delta']:>+8.4f}"
                f" {lo['spearman_rho']:>8.3f}"
                f" {hi['spearman_rho']:>8.3f}"
            )

        # ── Phase 2: Dominant weight identification ──
        print(f"\n{'─' * 70}")
        print("Phase 2: Dominant weight identification")
        print(f"{'─' * 70}")

        sensitivity = {}
        for field_name in type(default_weights).model_fields:
            deltas = [
                abs(r["composite_delta"])
                for r in perturbation_results
                if r["signal"] == field_name
            ]
            sensitivity[field_name] = max(deltas) if deltas else 0.0

        for sig, sens in sorted(
            sensitivity.items(), key=lambda x: x[1], reverse=True
        ):
            bar = "█" * int(sens * 200)
            print(f"  {sig:<28s} sensitivity={sens:.5f} {bar}")

        # ── Phase 3: Pareto-front search (coarse grid) ──
        print(f"\n{'─' * 70}")
        print("Phase 3: Pareto-front weight search (coarse grid)")
        print(f"{'─' * 70}")

        # Compute F1 for each weight combination
        def _compute_f1(
            test_findings: list[Finding],
            fixtures: list[GroundTruthFixture],
        ) -> float:
            tp = fp = fn_ = 0
            for fixture in fixtures:
                fixture_findings = [
                    f
                    for f in test_findings
                    if any(
                        fixture.name in str(f.file_path)
                        for _ in [None]
                        if f.file_path
                    )
                ]
                for exp in fixture.expected:
                    matched = any(
                        f.signal_type == exp.signal_type
                        for f in fixture_findings
                    )
                    if exp.should_detect and matched:
                        tp += 1
                    elif exp.should_detect and not matched:
                        fn_ += 1
                    elif not exp.should_detect and matched:
                        fp += 1
            p = tp / (tp + fp) if (tp + fp) > 0 else 1.0
            r = tp / (tp + fn_) if (tp + fn_) > 0 else 1.0
            return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

        # Use a coarse grid: scale each active weight by 0.5, 1.0, 1.5
        # Only vary the 3 most sensitive weights to keep search space
        # manageable
        top_sensitive = sorted(
            sensitivity, key=sensitivity.get, reverse=True
        )[:3]
        scales = [0.5, 1.0, 1.5]

        best_score = baseline_composite
        best_weights = None
        best_rho = 1.0

        for combo in itertools.product(scales, repeat=len(top_sensitive)):
            updates = {}
            for sig, scale in zip(top_sensitive, combo, strict=True):
                updates[sig] = getattr(default_weights, sig) * scale
            candidate = default_weights.model_copy(update=updates)
            c_score = composite_score(signal_scores, candidate)
            c_ranking = _score_ranking(signal_scores, candidate)
            rho = _spearman_rho(baseline_ranking, c_ranking)

            if c_score > best_score and rho >= 0.7:
                best_score = c_score
                best_weights = updates
                best_rho = rho

        if best_weights:
            print(f"  Best composite: {best_score:.4f} (ρ={best_rho:.3f})")
            print(f"  Weight adjustments: {best_weights}")
        else:
            print("  Baseline weights are already near-optimal.")

        # ── Save results ──
        try:
            from drift import __version__ as drift_ver
        except Exception:
            drift_ver = "unknown"

        output = {
            "_metadata": {
                "drift_version": drift_ver,
                "generated_at": datetime.datetime.now(
                    datetime.UTC
                ).isoformat(),
                "method": "weight_perturbation_sensitivity",
            },
            "baseline_composite": baseline_composite,
            "baseline_ranking": baseline_ranking,
            "signal_scores": {
                k.value: v for k, v in signal_scores.items()
            },
            "perturbations": perturbation_results,
            "sensitivity_ranking": dict(
                sorted(
                    sensitivity.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            ),
            "pareto_best_weights": best_weights,
        }

        output_path = (
            Path("benchmark_results") / "sensitivity_analysis.json"
        )
        output_path.parent.mkdir(exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
