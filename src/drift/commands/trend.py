"""drift trend — score trend over time."""

from __future__ import annotations

from pathlib import Path

import click

from drift.commands import console
from drift.trend_history import load_history, snapshot_scope


@click.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option("--last", "-l", "days", default=90, type=int, help="Number of days to trend.")
@click.option("--config", "-c", type=click.Path(path_type=Path), default=None)
def trend(repo: Path, days: int, config: Path | None) -> None:
    """Show drift score trend over time (requires git history)."""
    from rich.table import Table

    from drift.analyzer import analyze_repo
    from drift.config import DriftConfig

    cfg = DriftConfig.load(repo, config)
    history_file = repo / cfg.cache_dir / "history.json"

    console.print(f"[bold]Drift — trend ({days}-day history window)[/bold]")
    console.print()

    with console.status("[bold blue]Analyzing current state..."):
        analysis = analyze_repo(repo, cfg, since_days=days)

    # Analyzer persistiert den aktuellen Snapshot bereits kanonisch.
    snapshots = [s for s in load_history(history_file) if snapshot_scope(s) == "repo"]

    # Display trend table
    if len(snapshots) < 2:
        console.print(f"  Drift score: [bold]{analysis.drift_score:.3f}[/bold]")
        console.print(f"  Files: {analysis.total_files}  |  Findings: {len(analysis.findings)}")
        console.print()
        console.print("[dim]Run again later to see trend comparison.[/dim]")
        return

    table = Table(title="Score History (last 10)")
    table.add_column("Timestamp", min_width=20)
    table.add_column("Score", justify="right")
    table.add_column("Δ", justify="right")
    table.add_column("Findings", justify="right")

    recent = snapshots[-10:]
    for i, snap in enumerate(recent):
        ts = snap["timestamp"][:19].replace("T", " ")
        score = snap["drift_score"]
        findings = snap.get("total_findings", "?")

        if i > 0:
            prev = recent[i - 1]["drift_score"]
            delta = score - prev
            delta_str = f"{delta:+.3f}"
            if delta > 0.01:
                delta_str = f"[red]{delta_str}[/red]"
            elif delta < -0.01:
                delta_str = f"[green]{delta_str}[/green]"
        else:
            delta_str = "—"

        color = "red" if score >= 0.6 else "yellow" if score >= 0.3 else "green"
        table.add_row(ts, f"[{color}]{score:.3f}[/{color}]", delta_str, str(findings))

    console.print(table)
    console.print()

    # Summary
    first_score = snapshots[0]["drift_score"]
    latest_score = snapshots[-1]["drift_score"]
    overall_delta = latest_score - first_score
    direction = (
        "[red]↑ increasing[/red]"
        if overall_delta > 0.01
        else "[green]↓ decreasing[/green]"
        if overall_delta < -0.01
        else "[dim]→ stable[/dim]"
    )
    console.print(
        f"  Overall trend ({len(snapshots)} snapshots): {direction}  ({overall_delta:+.3f})"
    )

    console.print(f"  Current drift score: [bold]{analysis.drift_score:.2f}[/bold]")
    console.print(f"  Files analyzed: {analysis.total_files}")
    console.print(f"  Total findings: {len(analysis.findings)}")
    console.print(f"  AI-attributed commits: {analysis.ai_attributed_ratio:.0%}")

    # Trend chart
    if len(snapshots) >= 3:
        from drift.output.rich_output import render_trend_chart

        render_trend_chart(snapshots, console=console)
