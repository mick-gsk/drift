"""Output formatters for drift-cockpit: JSON, Rich terminal, SARIF 2.1.0 (Feature 006)."""

from __future__ import annotations

import json
from typing import Any

from drift_cockpit._models import DecisionBundle, DecisionStatus, LedgerEntry, OutcomeState

# ---------------------------------------------------------------------------
# JSON output (decision-bundle-v1)
# ---------------------------------------------------------------------------

_STATUS_COLORS: dict[DecisionStatus, str] = {
    DecisionStatus.go: "green",
    DecisionStatus.go_with_guardrails: "yellow",
    DecisionStatus.no_go: "red",
}

_STATUS_LABELS: dict[DecisionStatus, str] = {
    DecisionStatus.go: "GO",
    DecisionStatus.go_with_guardrails: "GO WITH GUARDRAILS",
    DecisionStatus.no_go: "NO-GO",
}


def bundle_to_json(bundle: DecisionBundle, *, indent: int = 2) -> str:
    """Serialise DecisionBundle to JSON string (decision-bundle-v1)."""
    raw = bundle.model_dump(by_alias=True)
    raw["schema"] = "decision-bundle-v1"
    raw["computed_at"] = bundle.computed_at.isoformat()
    return json.dumps(raw, indent=indent, default=str)


def bundle_to_sarif(bundle: DecisionBundle) -> str:
    """Emit SARIF 2.1.0 JSON from DecisionBundle risk drivers (Constitution IV)."""
    _SARIF_SEVERITY: dict[str, str] = {  # noqa: N806
        "critical": "error",
        "high": "error",
        "medium": "warning",
        "low": "note",
    }
    results: list[dict[str, Any]] = []
    for driver in bundle.top_risk_drivers:
        result: dict[str, Any] = {
            "ruleId": driver.driver_id,
            "level": _SARIF_SEVERITY.get(driver.severity.lower(), "warning"),
            "message": {"text": f"{driver.title} (impact={driver.impact:.3f})"},
        }
        if driver.source_refs:
            result["locations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {
                            "uri": driver.source_refs[0],
                            "uriBaseId": "%SRCROOT%",
                        }
                    }
                }
            ]
        results.append(result)

    sarif: dict[str, Any] = {
        "$schema": (
            "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/"
            "Schemata/sarif-schema-2.1.0.json"
        ),
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "drift-cockpit",
                        "version": "2.50.0",
                        "rules": [
                            {"id": d.driver_id, "name": d.title}
                            for d in bundle.top_risk_drivers
                        ],
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2, default=str)


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------


def bundle_to_rich(bundle: DecisionBundle, *, no_color: bool = False) -> None:
    """Print a rich Decision Panel for a DecisionBundle."""
    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        # Fallback to plain text
        print(f"Decision: {bundle.status} | Confidence: {bundle.confidence:.1%}")
        return

    con = Console(no_color=no_color)
    color = _STATUS_COLORS.get(bundle.status, "white")
    label = _STATUS_LABELS.get(bundle.status, bundle.status.value.upper())
    evidence_note = "" if bundle.evidence_sufficient else "  [dim](no evidence)[/dim]"

    # --- Status Panel ---
    con.print(
        Panel(
            f"[bold {color}]{label}[/bold {color}]{evidence_note}\n"
            f"Confidence: [bold]{bundle.confidence:.1%}[/bold]  "
            f"Risk score: [bold]{bundle.risk_score:.3f}[/bold]  "
            f"Version: {bundle.version}",
            title=f"[bold]drift cockpit[/bold] — PR [cyan]{bundle.pr_id}[/cyan]",
            border_style=color,
        )
    )

    # --- Risk Drivers Table ---
    if bundle.top_risk_drivers:
        table = Table(
            "Driver", "Impact", "Severity", "Files",
            box=box.SIMPLE_HEAD,
            show_header=True,
        )
        for driver in bundle.top_risk_drivers[:5]:
            table.add_row(
                driver.title,
                f"{driver.impact:.3f}",
                driver.severity,
                ", ".join(driver.source_refs[:2]) if driver.source_refs else "—",
            )
        con.print(Panel(table, title="Top Risk Drivers"))

    # --- Safe Plans ---
    if bundle.safe_plans:
        for plan in bundle.safe_plans:
            lines = [
                f"Expected risk delta: [yellow]{plan.expected_risk_delta:+.4f}[/yellow]  "
                f"Score delta: [green]{plan.expected_score_delta:+.4f}[/green]  "
                f"Target threshold: {plan.target_threshold:.0%}",
            ]
            for step in plan.steps:
                lines.append(f"  • {step.description}")
            con.print(Panel("\n".join(lines), title="Minimal Safe Plan"))

    # --- Risk Clusters ---
    if bundle.risk_clusters:
        ctable = Table("Cluster", "Risk Share", "Files", box=box.SIMPLE_HEAD)
        for cluster in bundle.risk_clusters:
            ctable.add_row(
                cluster.label,
                f"{cluster.risk_contribution:.1%}",
                str(len(cluster.files)),
            )
        con.print(Panel(ctable, title="Accountability Clusters"))


def ledger_to_rich(entries: list[LedgerEntry], *, no_color: bool = False) -> None:
    """Print a ledger timeline for a list of LedgerEntry objects."""
    try:
        from rich import box
        from rich.console import Console
        from rich.table import Table
    except ImportError:
        for e in entries:
            print(f"v{e.version}: {e.recommended_status} -> {e.human_status}")
        return

    con = Console(no_color=no_color)
    table = Table(
        "Ver", "Recommended", "Decision", "Override", "7d Outcome", "30d Outcome",
        box=box.SIMPLE_HEAD,
    )
    for e in entries:
        outcome_7 = (
            e.outcome_7d.state.value
            if e.outcome_7d.state != OutcomeState.pending
            else "[dim]pending[/dim]"
        )
        outcome_30 = (
            e.outcome_30d.state.value
            if e.outcome_30d.state != OutcomeState.pending
            else "[dim]pending[/dim]"
        )
        table.add_row(
            str(e.version),
            e.recommended_status.value,
            e.human_status.value,
            (e.override_reason[:30] + "…") if e.override_reason else "—",
            outcome_7,
            outcome_30,
        )
    from rich.panel import Panel
    con.print(Panel(table, title=f"Decision Ledger — PR {entries[0].pr_id if entries else '?'}"))
