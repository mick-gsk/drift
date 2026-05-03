"""drift start - guided onboarding path for first-time users (deprecated: use drift setup)."""

from __future__ import annotations

import click


@click.command("start", short_help="[deprecated] Use 'drift setup' instead.")
def start() -> None:
    """Onboarding entry point — replaced by the interactive 'drift setup' wizard.

    This command is kept for backwards compatibility. Use 'drift setup' for
    the interactive first-run experience.
    """
    click.echo(
        "Note: 'drift start' is superseded by the interactive wizard.\n"
        "      Run 'drift setup' for a personalised first-run experience.\n"
    )
    click.echo("The recommended three-step path:\n")
    click.echo("  1) drift setup              # personalised config in 3 questions")
    click.echo("  2) drift status             # traffic-light health check")
    click.echo("  3) drift analyze --repo .   # full findings with file references")
    click.echo("")
    click.echo("Tip: bare 'drift' (no subcommand) runs 'drift status' automatically.")
    click.echo("")
    click.echo("Learn more about any signal: drift explain PFS")
