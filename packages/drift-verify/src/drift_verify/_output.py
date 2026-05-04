"""Output formatters for EvidencePackage: JSON, Rich terminal, SARIF 2.1.0."""

from __future__ import annotations

import json
from typing import Any

from drift_verify._models import EvidencePackage, Severity, Verdict

# ---------------------------------------------------------------------------
# JSON output (evidence-package-v1)
# ---------------------------------------------------------------------------

def evidence_to_json(pkg: EvidencePackage, *, indent: int = 2) -> str:
    """Serialise EvidencePackage to JSON string (evidence-package-v1)."""
    raw = pkg.model_dump(by_alias=True)
    # Ensure schema field is present under "schema" key
    raw.setdefault("schema", "evidence-package-v1")
    # Convert frozenset flags to sorted list for JSON compatibility
    raw["flags"] = sorted(raw.get("flags", []))
    # Convert Path objects to strings
    raw["verified_at"] = pkg.verified_at.isoformat()
    return json.dumps(raw, indent=indent, default=str)


# ---------------------------------------------------------------------------
# SARIF 2.1.0 output (Constitution IV)
# ---------------------------------------------------------------------------

_SARIF_SEVERITY: dict[Severity, str] = {
    Severity.critical: "error",
    Severity.high: "error",
    Severity.medium: "warning",
    Severity.low: "note",
}


def evidence_to_sarif(pkg: EvidencePackage) -> str:
    """Emit SARIF 2.1.0 JSON from EvidencePackage."""
    results: list[dict[str, Any]] = []
    for v in pkg.violations:
        result: dict[str, Any] = {
            "ruleId": v.rule_id or v.violation_type.value,
            "level": _SARIF_SEVERITY.get(v.severity, "warning"),
            "message": {"text": v.message},
        }
        if v.file:
            location: dict[str, Any] = {
                "physicalLocation": {
                    "artifactLocation": {"uri": v.file, "uriBaseId": "%SRCROOT%"},
                }
            }
            if v.line:
                location["physicalLocation"]["region"] = {"startLine": v.line}
            result["locations"] = [location]
        results.append(result)

    sarif: dict[str, Any] = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "drift-verify",
                        "version": pkg.version,
                        "informationUri": "https://github.com/mick-gsk/drift",
                    }
                },
                "results": results,
            }
        ],
    }
    return json.dumps(sarif, indent=2)


# ---------------------------------------------------------------------------
# Rich terminal output
# ---------------------------------------------------------------------------

def evidence_to_rich(pkg: EvidencePackage, *, console: Any = None) -> None:
    """Print a Rich summary of EvidencePackage to the terminal."""
    try:
        from rich import box
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        c = console or Console()
    except ImportError:
        print(f"drift verify: {pkg.action_recommendation.verdict.value}")
        return

    verdict = pkg.action_recommendation.verdict
    verdict_colors = {
        Verdict.automerge: "bold green",
        Verdict.needs_fix: "bold red",
        Verdict.needs_review: "bold yellow",
        Verdict.escalate_to_human: "bold magenta",
    }
    color = verdict_colors.get(verdict, "white")

    c.print(
        Panel(
            f"[{color}]{verdict.value.upper()}[/{color}]\n"
            f"[dim]{pkg.action_recommendation.reason}[/dim]",
            title="[bold]drift verify[/bold]",
            expand=False,
        )
    )
    c.print(
        f"  Drift Score:       [cyan]{pkg.drift_score:.2f}[/cyan]  "
        f"  Spec Confidence:   [cyan]{pkg.spec_confidence_score:.2f}[/cyan]"
    )

    if pkg.violations:
        table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        table.add_column("Type", style="dim")
        table.add_column("Sev.")
        table.add_column("File")
        table.add_column("Message")
        sev_colors = {
            "critical": "bold red",
            "high": "red",
            "medium": "yellow",
            "low": "dim",
        }
        for v in pkg.violations:
            sc = sev_colors.get(v.severity.value, "")
            table.add_row(
                v.violation_type.value,
                f"[{sc}]{v.severity.value}[/{sc}]",
                v.file or "",
                v.message[:80],
            )
        c.print(table)

    if pkg.rule_promotions:
        c.print(f"[bold yellow]{len(pkg.rule_promotions)} rule promotion proposal(s)[/bold yellow]")
