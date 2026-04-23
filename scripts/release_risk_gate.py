#!/usr/bin/env python3
"""Composite Release Risk Gate.

Computes a weighted risk score from three KPI inputs:
  - F1 deficit       (weight 0.35): 1 - aggregate_f1   from kpi_snapshot.json
  - Mutation deficit (weight 0.35): 1 - overall_recall  from mutation_benchmark.json
  - Drift score      (weight 0.30): drift_score          from drift_self.json

Risk score range: 0.0 (perfect) – 1.0 (critical).
Default block threshold: 0.4.

Usage:
  python scripts/release_risk_gate.py \\
    --kpi benchmark_results/kpi_snapshot.json \\
    --mutation benchmark_results/mutation_benchmark.json \\
    --drift benchmark_results/drift_self.json \\
    --threshold 0.4

Exit codes:
  0 – risk score within acceptable range  (PASS)
  1 – risk score exceeds threshold        (BLOCK)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: file not found: {path}", flush=True)
        sys.exit(1)
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def _compute_risk(
    kpi: dict, mutation: dict, drift: dict
) -> tuple[float, dict[str, float]]:
    f1 = kpi.get("precision_recall", {}).get("aggregate_f1", 1.0)
    mutation_recall = mutation.get("overall_recall", 1.0)
    drift_score = drift.get("drift_score", 0.0)

    f1_deficit = max(0.0, 1.0 - float(f1))
    mutation_deficit = max(0.0, 1.0 - float(mutation_recall))
    drift_contribution = max(0.0, min(1.0, float(drift_score)))

    components: dict[str, float] = {
        "f1_deficit": round(f1_deficit, 4),
        "mutation_deficit": round(mutation_deficit, 4),
        "drift_score_contribution": round(drift_contribution, 4),
    }
    risk = 0.35 * f1_deficit + 0.35 * mutation_deficit + 0.30 * drift_contribution
    return round(risk, 4), components


def _write_github_output(key: str, value: str) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as fh:
            fh.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Composite release risk gate")
    parser.add_argument("--kpi", required=True, help="Path to kpi_snapshot.json")
    parser.add_argument(
        "--mutation", required=True, help="Path to mutation_benchmark.json"
    )
    parser.add_argument("--drift", required=True, help="Path to drift_self.json")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Block threshold (default: 0.4)",
    )
    args = parser.parse_args()

    kpi = _load(args.kpi)
    mutation = _load(args.mutation)
    drift_data = _load(args.drift)

    risk_score, components = _compute_risk(kpi, mutation, drift_data)
    verdict = "BLOCK" if risk_score > args.threshold else "PASS"

    print(f"Composite risk score: {risk_score:.4f}  (threshold: {args.threshold})")
    print(f"  f1_deficit              = {components['f1_deficit']:.4f}  (weight 0.35)")
    print(f"  mutation_deficit        = {components['mutation_deficit']:.4f}  (weight 0.35)")
    print(f"  drift_score_contribution = {components['drift_score_contribution']:.4f}  (weight 0.30)")
    print(f"Verdict: {verdict}", flush=True)

    _write_github_output("risk_score", str(risk_score))
    _write_github_output("verdict", verdict)

    if verdict == "BLOCK":
        print(
            f"::error::Release blocked -- composite risk score {risk_score:.4f} "
            f"exceeds threshold {args.threshold}",
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
