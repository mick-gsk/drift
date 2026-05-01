"""Click subcommand: drift verify."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from drift_verify._models import ChangeSet
from drift_verify._output import evidence_to_json, evidence_to_rich, evidence_to_sarif
from drift_verify._verify import verify


@click.command("evidence")
@click.option(
    "--diff",
    "diff_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to unified diff file.",
)
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Root of the repository being analysed.",
)
@click.option(
    "--spec",
    "spec_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to spec.md for Spec Confidence Score computation.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "rich", "sarif"], case_sensitive=False),
    default="rich",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--exit-zero",
    is_flag=True,
    default=False,
    help="Always exit 0 (useful for non-blocking CI checks).",
)
@click.option(
    "--no-reviewer",
    is_flag=True,
    default=False,
    help="Skip independent reviewer agent (network-free operation).",
)
@click.option(
    "--reviewer-timeout",
    type=float,
    default=60.0,
    show_default=True,
    help="Timeout in seconds for the reviewer agent.",
)
@click.option(
    "--threshold-drift",
    type=float,
    default=0.2,
    show_default=True,
    help="Max drift score for automerge verdict.",
)
@click.option(
    "--threshold-confidence",
    type=float,
    default=0.8,
    show_default=True,
    help="Min spec confidence score for automerge verdict.",
)
@click.option(
    "--promote-threshold",
    type=int,
    default=5,
    show_default=True,
    help="Occurrences before a rule promotion is proposed.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Write output to file instead of stdout.",
)
def evidence_cmd(
    diff_path: Path | None,
    repo_path: Path,
    spec_path: Path | None,
    output_format: str,
    exit_zero: bool,
    no_reviewer: bool,
    reviewer_timeout: float,
    threshold_drift: float,
    threshold_confidence: float,
    promote_threshold: int,
    output_path: Path | None,
) -> None:
    """Verify a diff against architecture rules and emit an Evidence Package."""
    # Read diff text
    diff_text = ""
    if diff_path is not None:
        try:
            diff_text = diff_path.read_text(encoding="utf-8")
        except OSError as exc:
            click.echo(f"Error reading diff file: {exc}", err=True)
            sys.exit(10)

    change_set = ChangeSet(
        diff_text=diff_text,
        repo_path=repo_path.resolve(),
        spec_path=spec_path,
    )

    pkg = verify(
        change_set,
        use_reviewer=not no_reviewer,
        reviewer_timeout=reviewer_timeout,
        threshold_drift=threshold_drift,
        threshold_confidence=threshold_confidence,
        promote_threshold=promote_threshold,
    )

    # Format output
    if output_format == "json":
        output_text = evidence_to_json(pkg)
    elif output_format == "sarif":
        output_text = evidence_to_sarif(pkg)
    else:
        output_text = None

    if output_text is not None:
        if output_path:
            output_path.write_text(output_text, encoding="utf-8")
        else:
            click.echo(output_text)
    else:
        evidence_to_rich(pkg)

    # Exit code
    if exit_zero:
        sys.exit(0)

    verdict_codes = {
        "automerge": 0,
        "needs_fix": 1,
        "needs_review": 2,
        "escalate_to_human": 3,
    }
    code = verdict_codes.get(pkg.action_recommendation.verdict.value, 0)
    sys.exit(code)
