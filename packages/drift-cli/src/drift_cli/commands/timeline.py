"""drift timeline — root-cause analysis of when drift began."""

from __future__ import annotations

from pathlib import Path

import click

from drift_cli.commands import console


@click.command()
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option("--since", "-s", default=90, type=int, help="Days of git history to analyze.")
@click.option("--config", "-c", type=click.Path(path_type=Path), default=None)
def timeline(repo: Path, since: int, config: Path | None) -> None:
    """Show when and why drift began in each module (root-cause analysis)."""
    from drift.analyzer import analyze_repo
    from drift.config import DriftConfig
    from drift.output.rich_output import render_timeline
    from drift.timeline import build_timeline

    cfg = DriftConfig.load(repo, config)

    with console.status("[bold blue]Analyzing repository..."):
        analysis = analyze_repo(repo, cfg, since_days=since)

    # Reuse commits and file_histories from analysis (no second git pass)
    with console.status("[bold blue]Building timeline..."):
        module_scores = {ms.path.as_posix(): ms.drift_score for ms in analysis.module_scores}
        tl = build_timeline(
            analysis.commits, analysis.file_histories, analysis.findings, module_scores
        )

    console.print()
    console.print(f"[bold]Drift Timeline — {repo.resolve().name}[/bold]  ({since}-day history)")
    render_timeline(tl, console)
