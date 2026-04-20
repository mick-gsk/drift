"""Phase 3 — Agent Handoff.

Generates an agent prompt that embeds the contracts as invisible constraints.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _render_constraint_block(contracts: list[dict[str, Any]]) -> str:
    """Render contracts as a constraint block for agent prompts."""
    lines: list[str] = []
    for c in contracts:
        severity_icon = {"critical": "🔴", "high": "🟡", "medium": "🟢"}.get(
            c.get("severity", "medium"), "⚪"
        )
        lines.append(
            f"- [{severity_icon} {c['severity'].upper()}] **{c['id']}**: "
            f"{c['description_technical']}"
        )
        if c.get("verification_signal") and c["verification_signal"] != "manual":
            lines.append(f"  Signal: `{c['verification_signal']}`")
    return "\n".join(lines)


def handoff(
    prompt: str,
    intent_data: dict[str, Any],
) -> str:
    """Execute Phase 3 — generate the agent prompt.

    Parameters
    ----------
    prompt:
        Original user prompt.
    intent_data:
        Validated ``drift.intent.json`` payload.

    Returns
    -------
    str
        Markdown agent prompt content.
    """
    contracts = intent_data.get("contracts", [])
    category = intent_data.get("category", "utility")

    lines: list[str] = [
        "# Agent-Auftrag",
        "",
        "## Ziel",
        "",
        f"> {prompt}",
        "",
        f"Kategorie: **{category}**",
        "",
        "## Constraints (automatisch generiert)",
        "",
        "Die folgenden Anforderungen MÜSSEN bei der Implementierung eingehalten werden.",
        "Nach jedem Modul / jeder Funktion stoppen und auf Validierung warten.",
        "",
        _render_constraint_block(contracts),
        "",
        "## Validierung",
        "",
        "Nach jeder Änderung wird `drift intent --phase 4` ausgeführt.",
        "Der Commit ist erst erlaubt, wenn alle Contracts den Status `fulfilled` haben.",
        "",
        "## Ablauf",
        "",
        "1. Implementiere die nächste Funktion / das nächste Modul",
        "2. Stoppe und warte auf `drift intent --phase 4`",
        "3. Behebe alle `violated`-Contracts",
        "4. Wiederhole bis alle Contracts `fulfilled` sind",
        "",
    ]

    return "\n".join(lines)


def save_agent_prompt(content: str, repo_path: Path) -> Path:
    """Write drift.agent.prompt.md to the repo root."""
    out = repo_path / "drift.agent.prompt.md"
    out.write_text(content, encoding="utf-8")
    return out
