"""CP3 Convergence-Gate: detect stagnating DSOL cycles before write-back.

Usage::

    python scripts/check_dsol_convergence.py \\
        --ledger .drift/self_improvement_ledger.jsonl \\
        --window 4 \\
        --fail-on-stagnation

Exit codes:
    0 — PROGRESSING (gate satisfied)
    1 — STAGNATING (gate not satisfied)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from drift.self_improvement.engine import _convergence_check


@click.command()
@click.option(
    "--ledger",
    "ledger_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=".drift/self_improvement_ledger.jsonl",
    show_default=True,
    help="Path to the DSOL cycle ledger JSONL file.",
)
@click.option(
    "--window",
    type=int,
    default=4,
    show_default=True,
    help="Number of recent cycles to consider for stagnation detection.",
)
@click.option(
    "--fail-on-stagnation",
    is_flag=True,
    default=False,
    help="Exit 1 if stagnation is detected.",
)
def main(ledger_path: Path, window: int, fail_on_stagnation: bool) -> None:
    """Check whether the DSOL cycle has stagnated (Convergence-Gate CP3)."""
    if not ledger_path.exists():
        result = {
            "gate": "convergence_gate",
            "ledger_path": str(ledger_path),
            "status": "no_ledger",
            "stagnating": False,
            "message": "ledger does not exist yet — first cycle is always fresh",
        }
        click.echo(json.dumps(result, indent=2))
        sys.exit(0)

    rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    convergence = _convergence_check(rows, window=window)

    if convergence is None:
        result = {
            "gate": "convergence_gate",
            "ledger_path": str(ledger_path),
            "status": "insufficient_data",
            "stagnating": False,
            "message": f"need at least 2 ledger rows (found {len(rows)})",
        }
        click.echo(json.dumps(result, indent=2))
        sys.exit(0)

    stagnating = convergence.stagnating
    result = {
        "gate": "convergence_gate",
        "ledger_path": str(ledger_path),
        "status": "stagnating" if stagnating else "progressing",
        "stagnating": stagnating,
        "overlap_ratio": convergence.overlap_ratio,
        "repeated_ids": list(convergence.repeated_ids),
        "window": convergence.window,
        "message": (
            f"overlap_ratio={convergence.overlap_ratio:.0%} across {convergence.window} cycles — "
            + ("STAGNATING (>50% repeated)" if stagnating else "progressing")
        ),
    }
    click.echo(json.dumps(result, indent=2))

    if fail_on_stagnation and stagnating:
        sys.exit(1)


if __name__ == "__main__":
    main()
