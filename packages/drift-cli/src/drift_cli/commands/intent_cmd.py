"""drift intent — capture and manage user intent contracts."""

from __future__ import annotations

from pathlib import Path

import click


@click.group(invoke_without_command=True)
@click.option(
    "--repo",
    "-r",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Path to the repository root.",
)
@click.option(
    "--description",
    "-d",
    default=None,
    help="Free-text description of your intent (non-interactive mode).",
)
@click.option(
    "--language",
    "--lang",
    default="de",
    help="Language for questions and output (ISO 639-1, default: de).",
)
@click.pass_context
def intent(ctx: click.Context, repo: Path, description: str | None, language: str) -> None:
    """Capture what you want your app to do — in plain language.

    \\b
    Interactive:
      drift intent                          # guided flow with questions
    \\b
    Non-interactive:
      drift intent -d "Eine Todo-App"       # classify and save directly
    \\b
    List saved intents:
      drift intent list
    """
    ctx.ensure_object(dict)
    ctx.obj["repo"] = repo
    ctx.obj["language"] = language

    if ctx.invoked_subcommand is not None:
        return

    # No subcommand → capture mode
    if description is None:
        # Interactive mode
        description = click.prompt("Was soll deine App können?")

    from drift.intent._classify import classify_intent
    from drift.intent._questions import generate_questions
    from drift.intent._store import save_contract

    contract = classify_intent(description, language=language)

    click.echo(f"\nKategorie: {contract.category.value}")
    click.echo(f"Anforderungen: {len(contract.requirements)}")

    for req in contract.requirements:
        click.echo(f"  • {req.description_plain}")

    # Generate and show clarifying questions
    questions = generate_questions(contract)
    if questions:
        click.echo("\nZusätzliche Fragen:")
        for i, q in enumerate(questions, 1):
            click.echo(f"\n  {i}. {q.question_text}")
            for j, opt in enumerate(q.options, 1):
                click.echo(f"     {j}) {opt}")

    # Save contract
    intent_file = save_contract(contract, repo)
    click.echo(f"\nContract gespeichert: {intent_file}")


@intent.command("list")
@click.pass_context
def intent_list(ctx: click.Context) -> None:
    """List all saved intent contracts."""
    from drift.intent._store import load_contracts

    repo = ctx.obj["repo"]
    contracts = load_contracts(repo)

    if not contracts:
        click.echo("Keine Intent-Contracts gefunden.")
        return

    for i, c in enumerate(contracts, 1):
        click.echo(f"\n[{i}] {c.description}")
        click.echo(f"    Kategorie: {c.category.value}")
        click.echo(f"    Sprache: {c.language}")
        click.echo(f"    Anforderungen: {len(c.requirements)}")
        for req in c.requirements:
            click.echo(f"      • {req.description_plain} [{req.priority}]")


@intent.command("run")
@click.argument("prompt", required=False, default=None)
@click.option(
    "--phase",
    type=click.IntRange(min=1, max=5),
    default=None,
    help="Run a single phase (1-5). Omit to run all phases.",
)
@click.option(
    "--max-repair-iterations",
    type=click.IntRange(min=1, max=10),
    default=3,
    help="Maximum repair loop iterations (phase 5).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Write JSON output to a file instead of stdout.",
)
@click.pass_context
def intent_run(
    ctx: click.Context,
    prompt: str | None,
    phase: int | None,
    max_repair_iterations: int,
    output: Path | None,
) -> None:
    """Run the 5-phase intent guarantor loop.

    Converts a natural-language prompt into verifiable contracts and
    validates them against the codebase.

    \\b
    Examples:
      drift intent run "Ich will eine App die meinen Kühlschrank verwaltet"
      drift intent run --phase 1 "Eine Todo-App mit Login"
      drift intent run --phase 4
    """
    from drift.api._util import to_json
    from drift.api.intent import intent as api_intent

    repo = ctx.obj["repo"]
    result = api_intent(
        prompt=prompt,
        path=repo,
        phase=phase,
        max_repair_iterations=max_repair_iterations,
    )
    text = to_json(result)
    if output is not None:
        output.write_text(text, encoding="utf-8")
        click.echo(f"Output written to {output}", err=True)
    else:
        click.echo(text)
