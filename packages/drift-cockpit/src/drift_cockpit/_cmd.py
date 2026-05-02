"""Click commands for drift cockpit subcommand group (Feature 006)."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import click

from drift_cockpit import build_decision_bundle
from drift_cockpit._exceptions import (
    MissingEvidenceError,
    MissingOverrideJustificationError,
    VersionConflictError,
)
from drift_cockpit._ledger import (
    read_ledger,
    update_outcome,
    write_ledger_entry,
)
from drift_cockpit._models import (
    DecisionStatus,
    LedgerEntry,
    OutcomeState,
)
from drift_cockpit._output import (
    bundle_to_json,
    bundle_to_rich,
    bundle_to_sarif,
    ledger_to_rich,
)

_DEFAULT_LEDGER_DIR = Path(".drift") / "cockpit"

# ---------------------------------------------------------------------------
# drift cockpit group
# ---------------------------------------------------------------------------


@click.group("cockpit")
def cockpit_cmd() -> None:
    """Human Decision Cockpit — merge governance with audit trail."""


# ---------------------------------------------------------------------------
# drift cockpit build
# ---------------------------------------------------------------------------


@cockpit_cmd.command("build")
@click.option("--pr", "pr_id", required=True, help="Pull Request identifier.")
@click.option(
    "--repo",
    "repo_path",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    show_default=True,
    help="Repository root to analyse.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "rich", "sarif"], case_sensitive=False),
    default="rich",
    show_default=True,
    help="Output format (json | rich | sarif).",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=None,
    help="Write output to file instead of stdout.",
)
@click.option(
    "--exit-zero",
    is_flag=True,
    default=False,
    help="Always exit 0 (useful for non-blocking CI checks).",
)
def build_cmd(
    pr_id: str,
    repo_path: Path,
    output_format: str,
    output_path: Path | None,
    exit_zero: bool,
) -> None:
    """Build a Decision Bundle for a Pull Request.

    Exit codes: 0=go, 1=guardrails, 2=no_go, 3=runtime error, 10=input error.
    """
    # Load findings from drift analysis
    try:
        from drift.api import analyze as _analyze
        result = _analyze(repo_path)
        findings = getattr(result, "findings", []) or []
    except Exception:
        findings = []

    # Load prior version from ledger (FR-009)
    existing = read_ledger(pr_id, base=_DEFAULT_LEDGER_DIR)
    prior_version = existing[-1].version if existing else None

    try:
        bundle = build_decision_bundle(pr_id, findings, prior_version=prior_version)
    except MissingEvidenceError:
        # Build a no_go bundle with empty findings for output
        from drift_cockpit._models import DecisionBundle
        bundle = DecisionBundle(
            pr_id=pr_id,
            status=DecisionStatus.no_go,
            confidence=0.0,
            evidence_sufficient=False,
            risk_score=0.0,
            version=(prior_version + 1) if prior_version is not None else 1,
        )

    if output_format == "json":
        text = bundle_to_json(bundle)
    elif output_format == "sarif":
        text = bundle_to_sarif(bundle)
    else:
        if output_path:
            # Fallback to JSON for file output in rich mode
            text = bundle_to_json(bundle)
        else:
            bundle_to_rich(bundle)
            _exit_for_status(bundle.status, exit_zero)
            return

    if output_path:
        output_path.write_text(text, encoding="utf-8")
        click.echo(f"Written to {output_path}", err=True)
    else:
        click.echo(text)

    _exit_for_status(bundle.status, exit_zero)


def _exit_for_status(status: DecisionStatus, exit_zero: bool) -> None:
    if exit_zero:
        return
    if status == DecisionStatus.go:
        sys.exit(0)
    elif status == DecisionStatus.go_with_guardrails:
        sys.exit(1)
    else:
        sys.exit(2)


# ---------------------------------------------------------------------------
# drift cockpit decide
# ---------------------------------------------------------------------------


@cockpit_cmd.command("decide")
@click.option("--pr", "pr_id", required=True, help="Pull Request identifier.")
@click.option(
    "--verdict",
    type=click.Choice(["go", "go_with_guardrails", "no_go"], case_sensitive=False),
    required=True,
    help="Human decision verdict.",
)
@click.option(
    "--recommendation",
    type=click.Choice(["go", "go_with_guardrails", "no_go"], case_sensitive=False),
    default=None,
    help="Override the app recommendation (defaults to latest bundle status).",
)
@click.option(
    "--justification",
    "override_reason",
    default=None,
    help="Override justification (required when verdict differs from recommendation).",
)
@click.option("--actor", default="maintainer", show_default=True, help="Decision actor name.")
@click.option(
    "--ledger-dir",
    "ledger_dir",
    type=click.Path(path_type=Path),
    default=str(_DEFAULT_LEDGER_DIR),
    show_default=True,
    help="Ledger directory path.",
)
def decide_cmd(
    pr_id: str,
    verdict: str,
    recommendation: str | None,
    override_reason: str | None,
    actor: str,
    ledger_dir: Path,
) -> None:
    """Record a human decision for a Pull Request in the Decision Ledger."""
    from pydantic import ValidationError

    existing = read_ledger(pr_id, base=ledger_dir)
    next_version = (existing[-1].version + 1) if existing else 1

    # Derive recommendation from last bundle if not explicitly given
    if recommendation is None and existing:
        recommendation = existing[-1].recommended_status.value
    if recommendation is None:
        recommendation = verdict  # default: assume agreement

    human_status = DecisionStatus(verdict)
    recommended_status = DecisionStatus(recommendation)

    try:
        entry = LedgerEntry(
            ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
            pr_id=pr_id,
            recommended_status=recommended_status,
            human_status=human_status,
            override_reason=override_reason or None,
            decision_actor=actor,
            evidence_refs=[],
            version=next_version,
        )
        write_ledger_entry(entry, base=ledger_dir)
    except (MissingOverrideJustificationError, ValidationError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(10)
    except VersionConflictError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(3)

    click.echo(
        f"Recorded: PR {pr_id} | {recommended_status.value} → {human_status.value} "
        f"(version {next_version})"
    )


# ---------------------------------------------------------------------------
# drift cockpit outcome
# ---------------------------------------------------------------------------


@cockpit_cmd.command("outcome")
@click.option("--pr", "pr_id", required=True, help="Pull Request identifier.")
@click.option(
    "--days",
    "days",
    type=click.Choice(["7", "30"], case_sensitive=False),
    required=True,
    help="Outcome window: 7 or 30 days.",
)
@click.option(
    "--state",
    type=click.Choice(["captured", "not_available"], case_sensitive=False),
    default="captured",
    show_default=True,
    help="Outcome state.",
)
@click.option("--rework-events", type=int, default=None, help="Number of rework events observed.")
@click.option(
    "--ledger-dir",
    "ledger_dir",
    type=click.Path(path_type=Path),
    default=str(_DEFAULT_LEDGER_DIR),
    show_default=True,
    help="Ledger directory path.",
)
def outcome_cmd(
    pr_id: str,
    days: str,
    state: str,
    rework_events: int | None,
    ledger_dir: Path,
) -> None:
    """Record a 7-day or 30-day outcome for a Pull Request."""
    try:
        entry = update_outcome(
            pr_id,
            window=f"{days}d",
            state=OutcomeState(state),
            rework_events=rework_events,
            base=ledger_dir,
        )
    except ValueError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(10)
    except VersionConflictError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(3)

    click.echo(
        f"Recorded {days}d outcome for PR {pr_id}: {state} (version {entry.version})"
    )


# ---------------------------------------------------------------------------
# drift cockpit view
# ---------------------------------------------------------------------------


@cockpit_cmd.command("view")
@click.option("--pr", "pr_id", required=True, help="Pull Request identifier.")
@click.option(
    "--ledger-dir",
    "ledger_dir",
    type=click.Path(path_type=Path),
    default=str(_DEFAULT_LEDGER_DIR),
    show_default=True,
    help="Ledger directory path.",
)
def view_cmd(pr_id: str, ledger_dir: Path) -> None:
    """View the Decision Ledger timeline for a Pull Request."""
    entries = read_ledger(pr_id, base=ledger_dir)
    if not entries:
        click.echo(f"No ledger entries found for PR '{pr_id}'.", err=True)
        sys.exit(1)
    ledger_to_rich(entries)


# ---------------------------------------------------------------------------
# drift cockpit serve
# ---------------------------------------------------------------------------


@cockpit_cmd.command("serve")
@click.option(
    "--port",
    default=8000,
    show_default=True,
    type=int,
    help="Port to listen on.",
)
@click.option(
    "--api-url",
    "api_url",
    default="http://localhost:8001",
    show_default=True,
    envvar="COCKPIT_API_URL",
    help="Base URL of the Drift Cockpit backend API.",
)
def serve_cmd(port: int, api_url: str) -> None:
    """Serve the Cockpit frontend and proxy API calls to the backend."""
    try:
        import uvicorn

        from drift_cockpit._serve import create_app
    except ImportError as exc:  # pragma: no cover
        click.echo(
            f"Missing dependency for serve command: {exc}\n"
            "Install with: pip install drift-cockpit[serve]",
            err=True,
        )
        sys.exit(1)

    app = create_app(api_url=api_url)
    click.echo(
        f"Drift Cockpit server starting on http://localhost:{port}\n"
        f"  Backend API: {api_url}\n"
        "  Press Ctrl+C to stop."
    )
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

