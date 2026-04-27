"""``drift kit`` — VS Code Copilot Chat integration scaffolding.

One-command bootstrap that copies the slash-command prompts into the user's
repository, wires up ``.vscode/settings.json`` and gitignores the session file.
Designed to be simpler than spec-kit: no extra CLI install, no separate tool —
``pip install drift-analyzer`` already ships everything.
"""
from __future__ import annotations

from pathlib import Path

import click

from drift.commands import console
from drift.drift_kit._init import init_kit


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
def init(repo: Path, *, force: bool) -> None:
    """Bootstrap drift-kit: prompt files, VS Code settings and .gitignore.

    Writes the three slash-command prompt files into ``.github/prompts/``,
    ensures ``chat.promptFilesLocations`` is set in ``.vscode/settings.json``
    and adds ``.vscode/drift-session.json`` to ``.gitignore``.

    Run ``drift analyze`` afterwards and the slash commands
    (``/drift-fix-plan``, ``/drift-export-report``, ``/drift-auto-fix-loop``)
    are immediately available in VS Code Copilot Chat.
    """
    result = init_kit(repo.resolve(), force=force)

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
        return

    console.print(
        "\n[bold]Next:[/bold] run [bold]drift analyze[/bold] and open VS Code "
        "Copilot Chat — type [bold]/drift-fix-plan[/bold] to get started.",
    )
