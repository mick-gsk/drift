"""drift check — CI-mode diff analysis."""

from __future__ import annotations

import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Literal, cast

import click
from rich.console import Console

from drift.commands._shared import (
    apply_baseline_filtering,
    apply_signal_filtering,
    build_effective_console,
    configure_machine_output_console,
    render_or_emit_output,
)
from drift.errors import EXIT_FINDINGS_ABOVE_THRESHOLD


def _print_check_result(
    analysis,
    threshold: str,
    quiet: bool,
    effective_console: Console,
    exit_zero: bool,
    diff_ref: str = "HEAD~1",
) -> None:
    from drift.scoring.engine import severity_gate_pass

    if not severity_gate_pass(analysis.findings, threshold):
        if not quiet:
            effective_console.print(
                f"\n[bold red]✗ Drift check failed:[/bold red] "
                f"findings at or above '{threshold}' severity.",
            )
        if not exit_zero:
            sys.exit(EXIT_FINDINGS_ABOVE_THRESHOLD)
        return

    if not quiet:
        effective_console.print(
            f"\n[bold green]✓ Drift check passed[/bold green] (threshold: {threshold}).",
        )
        if not analysis.findings and diff_ref == "HEAD~1":
            from rich.panel import Panel

            effective_console.print(
                Panel(
                    "[dim]drift check scans only changed files (vs. HEAD~1 by default).\n"
                    "To scan the full repository:  [bold]drift analyze --repo .[/bold]\n"
                    "To check more history:        [bold]drift check --diff HEAD~3[/bold][/dim]",
                    title="[dim]Note[/dim]",
                    border_style="dim",
                )
            )


@click.command(short_help="CI drift gate — diff analysis (also: drift gate).")
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
)
@click.option(
    "--path", "--target-path", "-p",
    "target_path",
    default=None,
    help="Restrict analysis to a subdirectory.",
)
@click.option("--diff", "diff_ref", default="HEAD~1", help="Git ref to diff against.")
@click.option(
    "--fail-on",
    type=click.Choice(["critical", "high", "medium", "low", "none"]),
    default=None,
    help="Exit code 1 if any finding at or above this severity. Use 'none' for report-only.",
)
@click.option(
    "--output-format",
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["rich", "json", "sarif", "csv", "agent-tasks", "github", "junit", "llm"]),
    default="rich",
    help="Output format. Choices: rich, json, sarif, csv, agent-tasks, github, junit, llm.",
)
@click.option(
    "--exit-zero",
    is_flag=True,
    default=False,
    help="Always exit with code 0, even when findings exceed the severity gate.",
)
@click.option(
    "--select",
    "--signals",
    "select_signals",
    default=None,
    help="Comma-separated signal IDs to include (e.g. PFS,AVS,MDS).",
)
@click.option(
    "--ignore",
    "ignore_signals",
    default=None,
    help="Comma-separated signal IDs to exclude (e.g. TVS,DIA).",
)
@click.option("--config", "-c", type=click.Path(path_type=Path), default=None)
@click.option(
    "--workers",
    "-w",
    default=None,
    type=click.IntRange(min=1),
    help="Parallel workers for file parsing.",
)
@click.option(
    "--worker-strategy",
    type=click.Choice(["fixed", "auto"]),
    default=None,
    help="Worker resolution strategy. fixed uses CPU fallback, auto enables conservative tuning.",
)
@click.option(
    "--load-profile",
    type=click.Choice(["conservative"]),
    default=None,
    help="Auto-tuning load profile (currently conservative only).",
)
@click.option(
    "--no-embeddings", is_flag=True, default=False, help="Disable embedding-based analysis."
)
@click.option("--embedding-model", default=None, help="Sentence-transformers model name.")
@click.option(
    "--since",
    "since_days",
    default=None,
    type=int,
    help="Days of git history to consider.",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    default=False,
    help="Minimal output: score, severity, finding count, exit code only.",
)
@click.option(
    "--no-code",
    is_flag=True,
    default=False,
    help="Suppress inline code snippets in rich output.",
)
@click.option(
    "--baseline",
    "baseline_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Filter out known findings from a baseline file.",
)
@click.option(
    "--output",
    "-o",
    "output_file",
    type=click.Path(path_type=Path),
    default=None,
    help="Write machine output (JSON/SARIF/CSV) to a file instead of stdout.",
)
@click.option(
    "--json",
    "json_shortcut",
    is_flag=True,
    default=False,
    help="Shortcut for --format json (agent-friendly).",
)
@click.option(
    "--compact",
    "compact_json",
    is_flag=True,
    default=False,
    help="Emit compact JSON optimized for agent/CI summaries.",
)
@click.option(
    "--no-color",
    "no_color",
    is_flag=True,
    default=False,
    help="Disable colored output (also respects NO_COLOR env variable).",
)
@click.option(
    "--save-baseline",
    "save_baseline_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Save the current findings as a baseline file after analysis.",
)
@click.option(
    "--max-findings",
    type=int,
    default=20,
    help="Maximum number of findings to display (default: 20).",
)
def check(
    repo: Path,
    target_path: str | None,
    diff_ref: str,
    fail_on: str | None,
    output_format: str,
    exit_zero: bool,
    select_signals: str | None,
    ignore_signals: str | None,
    config: Path | None,
    workers: int | None,
    worker_strategy: str | None,
    load_profile: str | None,
    no_embeddings: bool,
    embedding_model: str | None,
    since_days: int | None,
    quiet: bool,
    no_code: bool,
    baseline_file: Path | None,
    output_file: Path | None,
    json_shortcut: bool,
    compact_json: bool,
    no_color: bool,
    save_baseline_path: Path | None,
    max_findings: int,
) -> None:
    """CI gate — analyze a diff and exit non-zero when findings exceed a threshold.

    Use in CI pipelines and pre-merge checks.
    For detailed investigation, use ``analyze``.
    """
    from drift.analyzer import analyze_diff
    from drift.api_helpers import build_drift_score_scope, signal_scope_label
    from drift.config import DriftConfig
    if json_shortcut:
        output_format = "json"

    # Keep machine-readable payloads clean by routing shared console to stderr.
    configure_machine_output_console(output_format)
    effective_console = build_effective_console(no_color)

    cfg = DriftConfig.load(repo, config)
    if worker_strategy is not None:
        cfg.performance.worker_strategy = cast(Literal["fixed", "auto"], worker_strategy)
    if load_profile is not None:
        cfg.performance.load_profile = cast(Literal["conservative"], load_profile)
    if no_embeddings:
        cfg.embeddings_enabled = False
    if embedding_model:
        cfg.embedding_model = embedding_model
    if select_signals or ignore_signals:
        from drift.config import apply_signal_filter, resolve_signal_names

        apply_signal_filter(cfg, select_signals, ignore_signals)

    drift_score_scope = build_drift_score_scope(
        context="diff",
        path=target_path,
        signal_scope=signal_scope_label(
            selected=resolve_signal_names(select_signals) if select_signals else None,
            ignored=resolve_signal_names(ignore_signals) if ignore_signals else None,
        ),
        baseline_filtered=baseline_file is not None,
    )
    threshold = fail_on or cfg.severity_gate()

    effective_since = since_days if since_days is not None else 90
    status_console = Console(stderr=True) if output_format != "rich" else effective_console
    status_context = (
        nullcontext() if quiet else status_console.status("[bold blue]Checking diff...")
    )
    with status_context:
        analysis = analyze_diff(
            repo,
            cfg,
            diff_ref=diff_ref,
            workers=workers,
            since_days=effective_since,
            target_path=target_path,
        )

    apply_signal_filtering(analysis, cfg, select_signals, ignore_signals)
    apply_baseline_filtering(analysis, cfg, baseline_file)

    if quiet:
        sev = analysis.severity.value.upper()
        n = len(analysis.findings)
        click.echo(f"score: {analysis.drift_score:.3f}  severity: {sev}  findings: {n}")
    else:
        render_or_emit_output(
            analysis=analysis,
            output_format=output_format,
            compact_json=compact_json,
            drift_score_scope=drift_score_scope,
            output_file=output_file,
            effective_console=effective_console,
            max_findings=max_findings,
            no_code=no_code,
        )

    # Save baseline if requested (--save-baseline)
    if save_baseline_path is not None:
        from drift.baseline import save_baseline as _save_bl

        _save_bl(analysis, save_baseline_path)
        effective_console.print(
            f"[bold green]\u2713 Baseline saved:[/bold green] {save_baseline_path} "
            f"({len(analysis.findings)} findings)",
        )

    _print_check_result(
        analysis=analysis,
        threshold=threshold,
        quiet=quiet,
        effective_console=effective_console,
        exit_zero=exit_zero,
        diff_ref=diff_ref,
    )
