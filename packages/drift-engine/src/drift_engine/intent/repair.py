"""Phase 5 — Autonomous Repair Loop.

For violated contracts, generates repair prompts and re-validates
in a bounded loop.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from drift_engine.intent.models import ContractResult, ContractStatus
from drift_engine.intent.translator import escalation_message
from drift_engine.intent.validate import results_to_report_json, validate_contracts

_DEFAULT_MAX_ITERATIONS = 3


def _build_repair_prompt(violated: list[ContractResult]) -> str:
    """Generate a repair prompt for violated contracts.

    Parameters
    ----------
    violated:
        List of violated contract results.

    Returns
    -------
    str
        Markdown repair prompt.
    """
    lines: list[str] = [
        "# Reparatur-Auftrag",
        "",
        "Die folgenden Anforderungen sind noch nicht erfüllt.",
        "Bitte behebe die Probleme und warte dann auf eine erneute Prüfung.",
        "",
    ]

    for i, vr in enumerate(violated, 1):
        c = vr.contract
        lines.append(f"## Problem {i}: {c.description_human}")
        lines.append("")
        lines.append(f"- **Technisch:** {c.description_technical}")
        lines.append(f"- **Schwere:** {c.severity}")
        if vr.finding_id:
            lines.append(f"- **Betroffenes Signal:** {vr.finding_id}")
        if vr.finding_title:
            lines.append(f"- **Finding:** {vr.finding_title}")
        lines.append(f"- **Contract-ID:** {c.id}")
        lines.append(f"- **Nach der Reparatur muss gelten:** {c.description_human}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("Nach der Reparatur wird `drift intent --phase 4` erneut ausgeführt.")
    lines.append("")

    return "\n".join(lines)


def save_repair_prompt(content: str, repo_path: Path) -> Path:
    """Write drift.repair.prompt.md to the repo root."""
    out = repo_path / "drift.repair.prompt.md"
    out.write_text(content, encoding="utf-8")
    return out


def repair_loop(
    intent_data: dict[str, Any],
    repo_path: Path,
    *,
    max_iterations: int = _DEFAULT_MAX_ITERATIONS,
    findings: list[Any] | None = None,
    on_repair: Any = None,
) -> dict[str, Any]:
    """Execute Phase 5 — bounded autonomous repair loop.

    Parameters
    ----------
    intent_data:
        The ``drift.intent.json`` payload.
    repo_path:
        Repository root.
    max_iterations:
        Maximum repair attempts (default: 3).
    findings:
        Pre-computed findings for validation (used in testing).
    on_repair:
        Optional callback(repair_prompt: str, iteration: int) that
        applies the repair. If None, the loop writes the repair prompt
        and returns after one iteration (agent picks it up externally).

    Returns
    -------
    dict
        Final report with repair metadata.
    """
    prompt = intent_data.get("prompt", "")
    iteration = 0
    escalations: list[str] = []

    while iteration < max_iterations:
        # Validate
        results = validate_contracts(intent_data, repo_path, findings=findings)

        violated = [r for r in results if r.status == ContractStatus.VIOLATED]
        if not violated:
            # All fulfilled — success
            report = results_to_report_json(results, prompt=prompt, iteration=iteration)
            report["repair"] = {
                "iterations_used": iteration,
                "max_iterations": max_iterations,
                "status": "all_fulfilled",
                "escalations": [],
            }
            return report

        # Build repair prompt
        repair_prompt = _build_repair_prompt(violated)
        save_repair_prompt(repair_prompt, repo_path)

        iteration += 1

        if on_repair is not None:
            # Let the callback apply the repair (for testing / agent integration)
            import contextlib

            with contextlib.suppress(Exception):
                on_repair(repair_prompt, iteration)
        else:
            # No callback — return after writing repair prompt
            # (agent picks up drift.repair.prompt.md externally)
            report = results_to_report_json(results, prompt=prompt, iteration=iteration)
            report["repair"] = {
                "iterations_used": iteration,
                "max_iterations": max_iterations,
                "status": "repair_prompt_written",
                "escalations": [],
            }
            return report

    # Exhausted iterations — escalate remaining violated contracts
    final_results = validate_contracts(intent_data, repo_path, findings=findings)
    still_violated = [r for r in final_results if r.status == ContractStatus.VIOLATED]

    for vr in still_violated:
        escalations.append(escalation_message(vr, iteration))

    report = results_to_report_json(final_results, prompt=prompt, iteration=iteration)
    report["repair"] = {
        "iterations_used": iteration,
        "max_iterations": max_iterations,
        "status": "max_iterations_reached",
        "escalations": escalations,
    }
    return report
