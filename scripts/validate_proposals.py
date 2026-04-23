"""CP2 Score-Gate: validate that proposals meet quality thresholds before write-back.

Usage::

    python scripts/validate_proposals.py \\
        --proposals work_artifacts/improvement_report_<ts>.json \\
        --baseline 72.5 \\
        --current-score 71.8 \\
        --min-score 5.0 \\
        --fail-on-regression

Exit codes:
    0 — PASS (gate satisfied)
    1 — FAIL (gate not satisfied)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click


@click.command()
@click.option(
    "--proposals",
    "proposals_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to the ImprovementReport JSON from a DSOL cycle.",
)
@click.option(
    "--baseline",
    type=float,
    default=None,
    help="Baseline drift score (from drift-history branch). Required for regression gate.",
)
@click.option(
    "--current-score",
    type=float,
    default=None,
    help="Current drift score after the cycle.",
)
@click.option(
    "--min-score",
    type=float,
    default=0.0,
    show_default=True,
    help="Minimum proposal score required per proposal.",
)
@click.option(
    "--fail-on-regression",
    is_flag=True,
    default=False,
    help="Fail if current score has dropped more than 5 points below baseline.",
)
def main(
    proposals_path: Path,
    baseline: float | None,
    current_score: float | None,
    min_score: float,
    fail_on_regression: bool,
) -> None:
    """Validate DSOL proposals before write-back (Score-Gate CP2)."""
    raw = json.loads(proposals_path.read_text(encoding="utf-8"))
    proposals = raw.get("proposals") or []

    failures: list[str] = []

    # Gate 1: at least one proposal
    if not proposals:
        failures.append("no proposals in report — nothing to apply")

    # Gate 2: all proposals meet min-score
    if min_score > 0.0:
        below = [
            p.get("proposal_id") or "?"
            for p in proposals
            if isinstance(p, dict) and (p.get("score") or 0.0) < min_score
        ]
        if below:
            failures.append(
                f"{len(below)} proposal(s) below min-score {min_score}: "
                + ", ".join(below[:5])
            )

    # Gate 3: regression guard
    if fail_on_regression and baseline is not None and current_score is not None:
        threshold = baseline - 5.0
        if current_score < threshold:
            failures.append(
                f"current score {current_score:.1f} dropped >5 pts below "
                f"baseline {baseline:.1f} (threshold: {threshold:.1f})"
            )

    result = {
        "gate": "score_gate",
        "proposals_path": str(proposals_path),
        "proposal_count": len(proposals),
        "min_score": min_score,
        "baseline": baseline,
        "current_score": current_score,
        "pass": len(failures) == 0,
        "failures": failures,
    }
    click.echo(json.dumps(result, indent=2))

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
