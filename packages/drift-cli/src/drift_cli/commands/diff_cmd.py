"""drift diff — agent-native change-focused drift analysis."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

import click

from drift.api import diff as api_diff
from drift.api import to_json


def _run_fresh_analysis_to_json(path: Path) -> str:
    """Run a fresh repository analysis and return a drift-analyze JSON snapshot string.

    Extracted as a top-level function so tests can monkeypatch it cheaply.
    """
    from drift.analyzer import analyze_repo
    from drift.config import DriftConfig
    from drift.output.json_output import analysis_to_json

    cfg = DriftConfig.load(path)
    analysis = analyze_repo(path, cfg)
    return analysis_to_json(analysis, compact=False, response_detail="concise")


def _render_auto_diff(
    result: dict[str, Any],
    from_ts: str,
    *,
    from_finding_count: int,
) -> None:
    """Render the ``drift diff --auto`` output using Rich to stdout."""
    from rich.console import Console
    from rich.table import Table

    con = Console()

    score_before: float = float(result.get("score_before", 0.0))
    score_after: float = float(result.get("score_after", 0.0))
    delta: float = float(result.get("delta", 0.0))
    new_count: int = int(result.get("new_finding_count", 0))
    resolved_count: int = int(result.get("resolved_count", 0))
    new_findings: list[dict] = result.get("new_findings") or []
    resolved_findings: list[dict] = result.get("resolved_findings") or []
    to_finding_count = from_finding_count + new_count - resolved_count

    # ── Header ──────────────────────────────────────────────────────────────
    con.rule(f"[bold]drift diff --auto[/bold]  [dim](seit {from_ts})[/dim]")

    # ── Score row ────────────────────────────────────────────────────────────
    if delta < -0.001:
        delta_str = f"[green]▼ {abs(delta):.3f}[/green]"
        score_color = "green"
    elif delta > 0.001:
        delta_str = f"[red]▲ {delta:.3f}[/red]"
        score_color = "red"
    else:
        delta_str = "[dim]── 0.000[/dim]"
        score_color = "dim"

    con.print(
        f"Score:    {score_before:.3f} → [{score_color}]{score_after:.3f}[/{score_color}]"
        f"   {delta_str}"
    )

    # ── Findings summary row ──────────────────────────────────────────────────
    finding_delta = to_finding_count - from_finding_count
    if finding_delta < 0:
        fd_str = f"[green]{finding_delta}[/green]"
    elif finding_delta > 0:
        fd_str = f"[red]+{finding_delta}[/red]"
    else:
        fd_str = "[dim]0[/dim]"

    con.print(
        f"Findings: {from_finding_count} → {to_finding_count}   {fd_str}"
        f"   ([green]{resolved_count} resolved[/green] / [red]{new_count} new[/red])"
    )

    no_change = new_count == 0 and resolved_count == 0 and abs(delta) <= 0.001
    if no_change:
        con.print("\n[bold dim]Keine Änderung gegenüber letztem Scan.[/bold dim]")
        return

    # ── Per-signal breakdown table ────────────────────────────────────────────
    signal_new: dict[str, int] = {}
    signal_resolved: dict[str, int] = {}
    for f in new_findings:
        sig = str(f.get("signal") or "?")
        signal_new[sig] = signal_new.get(sig, 0) + 1
    for f in resolved_findings:
        sig = str(f.get("signal") or "?")
        signal_resolved[sig] = signal_resolved.get(sig, 0) + 1

    all_signals = sorted(set(signal_new) | set(signal_resolved))
    if all_signals:
        table = Table(show_header=True, header_style="bold", box=None, padding=(0, 2))
        table.add_column("Signal")
        table.add_column("Resolved", style="green", justify="right")
        table.add_column("New", style="red", justify="right")
        for sig in all_signals:
            table.add_row(
                sig,
                str(signal_resolved.get(sig, 0)) if sig in signal_resolved else "─",
                str(signal_new.get(sig, 0)) if sig in signal_new else "─",
            )
        con.print()
        con.print(table)

    # ── Resolved findings ─────────────────────────────────────────────────────
    if resolved_findings:
        con.print()
        con.print(f"[bold green]Resolved ({resolved_count}):[/bold green]")
        for f in resolved_findings:
            _print_finding_line(con, f, style="green")
        if resolved_count > len(resolved_findings):
            con.print(f"  [dim]… and {resolved_count - len(resolved_findings)} more[/dim]")

    # ── New findings ──────────────────────────────────────────────────────────
    if new_findings:
        con.print()
        con.print(f"[bold red]New ({new_count}):[/bold red]")
        for f in new_findings:
            _print_finding_line(con, f, style="red")
        if new_count > len(new_findings):
            con.print(f"  [dim]… and {new_count - len(new_findings)} more[/dim]")


def _print_finding_line(console: Any, finding: dict, *, style: str) -> None:
    """Print a single finding as a compact one-liner."""
    file_part = finding.get("file") or "?"
    line_part = finding.get("start_line")
    loc = f"{file_part}:{line_part}" if line_part else file_part
    title = finding.get("title") or "?"
    sig = finding.get("signal") or ""
    sig_tag = f"[{sig}] " if sig else ""
    console.print(f"  [{style}]{sig_tag}{loc}[/{style}] — {title}")


@click.command("diff")
@click.option(
    "--repo",
    "path",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    help="Path to the repository root.",
)
@click.option("--diff-ref", default="HEAD~1", help="Git ref to diff against.")
@click.option(
    "--uncommitted",
    is_flag=True,
    default=False,
    help="Analyze current working-tree changes against HEAD.",
)
@click.option(
    "--staged-only",
    is_flag=True,
    default=False,
    help="Analyze only staged changes.",
)
@click.option(
    "--target-path",
    "--path",
    default=None,
    help="Restrict decision logic to a subdirectory while surfacing out-of-scope noise.",
)
@click.option(
    "--baseline",
    "baseline_file",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Optional baseline file for new/resolved comparison.",
)
@click.option(
    "--from-file",
    "from_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Offline diff: source analyze JSON snapshot.",
)
@click.option(
    "--to-file",
    "to_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Offline diff: target analyze JSON snapshot.",
)
@click.option(
    "--auto",
    "-a",
    "auto",
    is_flag=True,
    default=False,
    help=(
        "Auto-diff: compare with the last saved scan snapshot (.drift-cache/last_scan.json). "
        "Runs a fresh analysis and shows score delta + resolved/new findings. "
        "Requires a prior 'drift analyze' run."
    ),
)
@click.option("--max-findings", type=int, default=10, help="Maximum findings to return.")
@click.option(
    "--response-detail",
    type=click.Choice(["concise", "detailed"]),
    default="concise",
    help="Response detail level.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write JSON output to a file instead of stdout.",
)
@click.option(
    "--signals",
    default=None,
    help="Comma-separated signal abbreviations to include (e.g. 'PFS,BEM').",
)
@click.option(
    "--exclude-signals",
    default=None,
    help="Comma-separated signal abbreviations to exclude (e.g. 'MDS,DIA').",
)
def diff(
    path: Path,
    diff_ref: str,
    uncommitted: bool,
    staged_only: bool,
    target_path: str | None,
    baseline_file: Path | None,
    from_file: Path | None,
    to_file: Path | None,
    auto: bool,
    max_findings: int,
    response_detail: str,
    output: Path | None,
    signals: str | None,
    exclude_signals: str | None,
) -> None:
    """Run agent-native diff analysis and emit structured JSON.

    Use --auto for a quick post-fix feedback loop without specifying commits:

    \b
      drift analyze          # run once to save snapshot
      # … apply fixes …
      drift diff --auto      # compare: score delta + resolved/new findings
    """
    if uncommitted and staged_only:
        raise click.UsageError("Use either --uncommitted or --staged-only, not both.")
    if (from_file is None) ^ (to_file is None):
        raise click.UsageError("Use --from-file and --to-file together.")

    signal_list = [s.strip() for s in signals.split(",") if s.strip()] if signals else None
    exclude_list = (
        [s.strip() for s in exclude_signals.split(",") if s.strip()] if exclude_signals else None
    )

    # ── --auto mode ───────────────────────────────────────────────────────────
    if auto:
        if from_file is not None or to_file is not None:
            raise click.UsageError(
                "--auto is incompatible with --from-file / --to-file. "
                "Use either --auto or --from-file/--to-file."
            )
        if uncommitted:
            raise click.UsageError(
                "--auto is incompatible with --uncommitted. "
                "Use --auto on its own for post-fix comparison."
            )

        from drift.config import DriftConfig

        cfg = DriftConfig.load(path)
        last_scan_path = path / cfg.cache_dir / "last_scan.json"

        if not last_scan_path.exists():
            raise click.ClickException(
                f"Kein vorheriger Scan-Snapshot gefunden ({last_scan_path}).\n"
                "Führe zuerst 'drift analyze' aus, um einen Snapshot zu speichern."
            )

        # Read metadata from last scan for display
        try:
            raw_last = json.loads(last_scan_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise click.ClickException(
                f"last_scan.json konnte nicht gelesen werden: {exc}\n"
                "Führe 'drift analyze' erneut aus, um den Snapshot zu erneuern."
            ) from exc

        from_ts: str = str(raw_last.get("analyzed_at") or "unbekannt")
        from_finding_count: int = len(raw_last.get("findings") or [])

        # Run fresh analysis → temp file
        fresh_json = _run_fresh_analysis_to_json(path)
        tmp_file: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(suffix=".json", prefix="drift_auto_")
            tmp_file = Path(tmp_name)
            import os

            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(fresh_json)

            auto_result = api_diff(
                path,
                from_file=str(last_scan_path),
                to_file=str(tmp_file),
                max_findings=max_findings,
                response_detail=response_detail,
                signals=signal_list,
                exclude_signals=exclude_list,
            )
        finally:
            if tmp_file is not None and tmp_file.exists():
                tmp_file.unlink(missing_ok=True)

        _render_auto_diff(auto_result, from_ts, from_finding_count=from_finding_count)

        if int(auto_result.get("new_high_or_critical", 0)) > 0:
            raise click.exceptions.Exit(1)
        return

    # ── Standard diff mode ────────────────────────────────────────────────────
    result = api_diff(
        path,
        diff_ref=diff_ref,
        uncommitted=uncommitted,
        staged_only=staged_only,
        baseline_file=str(baseline_file) if baseline_file else None,
        from_file=str(from_file) if from_file else None,
        to_file=str(to_file) if to_file else None,
        target_path=target_path,
        max_findings=max_findings,
        response_detail=response_detail,
        signals=signal_list,
        exclude_signals=exclude_list,
    )
    text = to_json(result)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
        click.echo(f"Output written to {output}", err=True)
    else:
        click.echo(text)

    # Offline mode follows issue #355 success criterion:
    # exit 1 when newly introduced HIGH/CRITICAL findings are present.
    if (
        from_file is not None
        and to_file is not None
        and int(result.get("new_high_or_critical", 0)) > 0
    ):
        raise click.exceptions.Exit(1)
