"""Click subcommand: drift pr-loop (T014, T034)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
from drift.config._loader import DriftConfig
from drift.pr_loop._engine import loop_until_approved
from drift.pr_loop._models import LoopExitStatus
from drift.pr_loop._output import render_json, render_rich

_EXIT_CODES = {
    LoopExitStatus.APPROVED: 0,
    LoopExitStatus.ESCALATED: 1,
    LoopExitStatus.ERROR: 2,
    LoopExitStatus.RUNNING: 2,
}


@click.command("pr-loop")
@click.argument("pr_number", type=int)
@click.option("--repo", default=None, help="GitHub repo (owner/repo). Auto-detected if omitted.")
@click.option("--config", "config_path", default="drift.yaml", show_default=True, type=click.Path())
@click.option(
    "--format",
    "output_format",
    default="rich",
    type=click.Choice(["rich", "json"]),
    show_default=True,
)
@click.option("--dry-run", is_flag=True, default=False, help="No GitHub side-effects.")
@click.option("--exit-zero", is_flag=True, default=False, help="Always exit 0.")
def pr_loop_cmd(
    pr_number: int,
    repo: str | None,
    config_path: str,
    output_format: str,
    dry_run: bool,
    exit_zero: bool,
) -> None:
    """Drive a GitHub PR through an automated agent review loop.

    Runs local gates, posts a self-review, requests configured reviewers,
    and iterates until all reviewers approve or max rounds is reached.
    """
    # Precondition: gh auth status (T014)
    try:
        subprocess.run(
            ["gh", "auth", "status"],
            check=True,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        click.echo(
            "Precondition failed: gh CLI not authenticated. Run 'gh auth login'.",
            err=True,
        )
        sys.exit(0 if exit_zero else 3)

    # Load config
    try:
        cfg = DriftConfig.load(Path(config_path).parent)
    except Exception as exc:
        click.echo(f"Failed to load config from {config_path}: {exc}", err=True)
        sys.exit(0 if exit_zero else 3)

    if cfg.pr_loop is None:
        click.echo(
            "No 'pr_loop:' section in drift.yaml. Add one to use 'drift pr-loop'.",
            err=True,
        )
        sys.exit(0 if exit_zero else 3)

    artifacts_dir = Path("work_artifacts")

    try:
        state = loop_until_approved(
            pr_number=pr_number,
            config=cfg.pr_loop,
            artifacts_dir=artifacts_dir,
            dry_run=dry_run,
        )
    except Exception as exc:
        click.echo(f"Loop failed with error: {exc}", err=True)
        sys.exit(0 if exit_zero else 2)

    if output_format == "json":
        click.echo(render_json(state, pr_number, cfg.pr_loop.reviewers))
    else:
        render_rich(state, pr_number)

    exit_code = _EXIT_CODES.get(state.status, 2)
    sys.exit(0 if exit_zero else exit_code)
