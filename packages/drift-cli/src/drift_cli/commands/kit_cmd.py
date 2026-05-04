"""``drift kit`` — VS Code Copilot Chat integration scaffolding.

One-command bootstrap that copies the slash-command prompts into the user's
repository, wires up ``.vscode/settings.json`` and gitignores the session file.
Designed to be simpler than spec-kit: no extra CLI install, no separate tool —
``pip install drift-analyzer`` already ships everything.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click

from drift.drift_kit._init import init_kit
from drift_cli.commands import console


@click.group("kit")
def kit() -> None:
    """drift-kit — VS Code Copilot Chat workflow integration."""


@kit.command("init")
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Repository root (default: current directory).",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite existing prompt files. settings.json is always merged safely.",
)
@click.option(
    "--and-analyze",
    "and_analyze",
    is_flag=True,
    default=False,
    help="Run 'drift analyze' automatically after scaffolding.",
)
@click.option(
    "--agent",
    "agents",
    type=click.Choice(["cursor", "claude", "codex", "all"]),
    multiple=True,
    default=(),
    help=(
        "Additional agent targets to configure (repeat for multiple)."
        " cursor: .cursor/rules/drift.mdc;"
        " claude: section in CLAUDE.md;"
        " codex: section in AGENTS.md;"
        " all: all of the above."
    ),
)
def init(repo: Path, *, force: bool, and_analyze: bool, agents: tuple[str, ...]) -> None:
    """Bootstrap drift-kit: prompt files, VS Code settings and .gitignore.

    Writes the four slash-command prompt files into ``.github/prompts/``,
    ensures ``chat.promptFilesLocations`` is set in ``.vscode/settings.json``
    and adds ``.vscode/drift-session.json`` to ``.gitignore``.

    Run ``drift analyze`` afterwards and the slash commands
    (``/drift-fix-plan``, ``/drift-export-report``, ``/drift-auto-fix-loop``,
    ``/drift-feature-guardrails``) are immediately available in VS Code Copilot Chat.
    """
    result = init_kit(repo.resolve(), force=force, agents=agents)

    if result.created:
        console.print("[bold green]Created[/bold green]")
        for path in result.created:
            console.print(f"  + {path}")
    if result.updated:
        console.print("[bold cyan]Updated[/bold cyan]")
        for path in result.updated:
            console.print(f"  ~ {path}")
    if result.skipped:
        console.print("[dim]Skipped (already present)[/dim]")
        for path in result.skipped:
            console.print(f"  = {path}")

    if not (result.created or result.updated):
        console.print(
            "\n[bold green]drift-kit is already set up.[/bold green] "
            "Run [bold]drift analyze[/bold] to refresh the session.",
        )
        if and_analyze:
            _run_analyze(repo.resolve())
        return

    if and_analyze:
        console.print(
            "\n[dim]Running drift analyze...[/dim]",
        )
        _run_analyze(repo.resolve())
    else:
        console.print(
            "\n[bold]Next:[/bold] run [bold]drift analyze[/bold] and open VS Code "
            "Copilot Chat — type [bold]/drift-fix-plan[/bold] to get started.",
        )


def _run_analyze(repo: Path) -> None:
    """Run ``drift analyze`` as a subprocess against *repo*."""
    proc = subprocess.run(
        [sys.executable, "-m", "drift", "analyze", "--repo", str(repo), "--exit-zero"],
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if proc.returncode == 0:
        console.print(
            "[bold green]Analysis complete.[/bold green] "
            "Open VS Code Copilot Chat and type [bold]/drift-fix-plan[/bold] to get started."
        )
    else:
        console.print(
            "[yellow]Analysis returned a non-zero exit code. "
            "Check the output above for details.[/yellow]"
        )
