"""``drift self-improve`` — run one Self-Improvement Loop cycle (ADR-097)."""

from __future__ import annotations

import json
from pathlib import Path

import click

from drift.self_improvement import run_cycle


@click.group(name="self-improve")
def self_improve() -> None:
    """Drift Self-Improvement Loop (DSOL).

    Runs a single bounded analysis cycle on the drift repo itself
    and emits human-reviewable proposals — never an automatic patch.
    Designed to be invoked weekly from a cron workflow so optimization
    pressure compounds over time without requiring agent autonomy.
    """


@self_improve.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Repository root.",
)
@click.option(
    "--max-proposals",
    type=int,
    default=10,
    show_default=True,
    help="Hard cap on proposals per cycle (flood guard).",
)
@click.option(
    "--trend-window",
    type=int,
    default=5,
    show_default=True,
    help="KPI snapshots to consider for slope detection.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
)
def run(repo: Path, max_proposals: int, trend_window: int, output_format: str) -> None:
    """Run one DSOL cycle and print a brief summary."""
    report = run_cycle(
        repo=repo,
        max_proposals=max_proposals,
        trend_window=trend_window,
    )

    if output_format == "json":
        click.echo(report.model_dump_json(indent=2))
        return

    click.echo(f"Self-Improvement cycle: {report.cycle_ts}")
    click.echo(f"Proposals: {len(report.proposals)}")
    for obs in report.observations:
        click.echo(f"  ! {obs}")
    for p in report.proposals:
        marker = "*" if p.recurrence > 1 else "-"
        click.echo(f"  {marker} [{p.kind}] {p.proposal_id} (score={p.score})")
    click.echo(
        f"Artifacts: work_artifacts/self_improvement/{report.cycle_ts}/ "
        f"(proposals.json, summary.md)"
    )


@self_improve.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Repository root.",
)
def ledger(repo: Path) -> None:
    """Show the recurrence ledger of past cycles (read-only)."""
    ledger_path = Path(repo) / ".drift" / "self_improvement_ledger.jsonl"
    if not ledger_path.exists():
        click.echo("no ledger yet — run `drift self-improve run` first.")
        return
    rows = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    for row in rows[-20:]:
        ids = row.get("proposal_ids") or []
        click.echo(f"{row.get('cycle_ts')}  ({len(ids)} proposals)")
