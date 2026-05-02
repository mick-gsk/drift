"""drift scan — agent-native repository scan."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import click
from drift.api import scan as api_scan
from drift.api import to_json
from drift_cli.commands._io import _is_non_tty_stdout, _write_output_file

_progress_start: float = 0.0


def _json_progress_callback(phase: str, current: int, total: int) -> None:
    """Emit structured JSON-lines progress on stderr for agent consumption."""
    msg = {
        "type": "progress",
        "step": current,
        "total": total,
        "signal": phase,
        "elapsed_s": round(time.monotonic() - _progress_start, 1),
    }
    sys.stderr.write(json.dumps(msg) + "\n")
    sys.stderr.flush()


@click.command("scan")
@click.option(
    "--repo",
    "path",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    help="Path to the repository root.",
)
@click.option("--target-path", "--path", default=None, help="Restrict analysis to a subdirectory.")
@click.option("--since", "since_days", type=int, default=90, help="Days of git history.")
@click.option(
    "--select",
    "--signals",
    "select",
    default=None,
    help="Comma-separated signal IDs to include (e.g. PFS,AVS).",
)
@click.option(
    "--exclude-signals",
    "--exclude",
    "--ignore",
    "exclude",
    default=None,
    help="Comma-separated signal IDs to exclude (e.g. MDS,DIA).",
)
@click.option(
    "--max-findings",
    type=click.IntRange(min=1, max=200),
    default=10,
    help="Maximum findings to return (1-200).",
)
@click.option(
    "--max-per-signal",
    type=click.IntRange(min=1, max=200),
    default=None,
    help="Maximum findings per signal in the returned list.",
)
@click.option(
    "--strategy",
    type=click.Choice(["diverse", "top-severity"]),
    default="diverse",
    help="Finding selection strategy: diverse (default) or top-severity.",
)
@click.option(
    "--response-detail",
    type=click.Choice(["concise", "detailed"]),
    default="concise",
    help="Response detail level.",
)
@click.option(
    "--include-non-operational",
    is_flag=True,
    default=False,
    help="Include fixture/generated/migration/docs findings in prioritization queues.",
)
@click.option(
    "--progress",
    type=click.Choice(["auto", "json", "none"]),
    default="auto",
    help="Progress reporting: auto (silent), json (JSON-lines on stderr), none.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write JSON output to a file instead of stdout.",
)
def scan(
    path: Path,
    target_path: str | None,
    since_days: int,
    select: str | None,
    exclude: str | None,
    max_findings: int,
    max_per_signal: int | None,
    strategy: str,
    response_detail: str,
    include_non_operational: bool,
    progress: str,
    output: Path | None,
) -> None:
    """Run the agent-native scan workflow and emit structured JSON."""

    # Auto-detect: use JSON progress for non-TTY consumers (#155)
    if progress == "auto" and _is_non_tty_stdout():
        progress = "json"

    progress_cb = None
    if progress == "json":
        global _progress_start
        _progress_start = time.monotonic()
        progress_cb = _json_progress_callback

    signals = [item.strip() for item in select.split(",") if item.strip()] if select else None
    exclude_signals = (
        [item.strip() for item in exclude.split(",") if item.strip()] if exclude else None
    )
    result = api_scan(
        path,
        target_path=target_path,
        since_days=since_days,
        signals=signals,
        exclude_signals=exclude_signals,
        max_findings=max_findings,
        max_per_signal=max_per_signal,
        response_detail=response_detail,
        strategy=strategy,
        include_non_operational=include_non_operational,
        on_progress=progress_cb,
    )
    text = to_json(result)
    if output is not None:
        _write_output_file(text, output)
        click.echo(f"Output written to {output}", err=True)
    else:
        click.echo(text)
