"""Render negative context items for agent consumption.

Supports three output formats:
- ``instructions``: compatible with ``.instructions.md`` / copilot-instructions
- ``prompt``: compact summary for system prompt usage
- ``raw``: machine-readable JSON payload for automation pipelines
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from drift.models import (
    NegativeContext,
    NegativeContextCategory,
    Severity,
)

# ---------------------------------------------------------------------------
# Category labels for section headings
# ---------------------------------------------------------------------------

_CATEGORY_HEADING: dict[NegativeContextCategory, str] = {
    NegativeContextCategory.SECURITY: "Security Anti-Patterns",
    NegativeContextCategory.ERROR_HANDLING: "Error Handling Anti-Patterns",
    NegativeContextCategory.ARCHITECTURE: "Architecture Anti-Patterns",
    NegativeContextCategory.TESTING: "Testing Anti-Patterns",
    NegativeContextCategory.NAMING: "Naming Anti-Patterns",
    NegativeContextCategory.COMPLEXITY: "Complexity Anti-Patterns",
    NegativeContextCategory.COMPLETENESS: "Completeness Anti-Patterns",
}

_SEVERITY_ICON: dict[Severity, str] = {
    Severity.CRITICAL: "🔴",
    Severity.HIGH: "🟠",
    Severity.MEDIUM: "🟡",
    Severity.LOW: "🔵",
    Severity.INFO: "⚪",
}

# Merge markers for safe update of existing files
MARKER_BEGIN = (
    "<!-- drift:negative-context:begin"
    " -- auto-generated anti-pattern constraints from drift -->"
)
MARKER_END = "<!-- drift:negative-context:end -->"


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render_item(nc: NegativeContext) -> str:
    """Render a single NegativeContext as a Markdown list entry."""
    icon = _SEVERITY_ICON.get(nc.severity, "")
    lines: list[str] = []

    lines.append(
        f"- {icon} **{nc.description}** "
        f"({nc.source_signal.value}, {nc.severity.value})"
    )

    if nc.forbidden_pattern:
        lines.append(f"  - **DO NOT:** {nc.forbidden_pattern}")

    if nc.canonical_alternative:
        lines.append(f"  - **INSTEAD:** {nc.canonical_alternative}")

    if nc.affected_files:
        shown = nc.affected_files[:5]
        paths = ", ".join(f"`{f}`" for f in shown)
        suffix = (
            f" (+{len(nc.affected_files) - 5} more)"
            if len(nc.affected_files) > 5
            else ""
        )
        lines.append(f"  - Affected: {paths}{suffix}")

    return "\n".join(lines)


def _group_by_category(
    items: list[NegativeContext],
) -> dict[NegativeContextCategory, list[NegativeContext]]:
    """Group items by category, preserving sort order within groups."""
    groups: dict[NegativeContextCategory, list[NegativeContext]] = {}
    for item in items:
        groups.setdefault(item.category, []).append(item)
    return groups


def _render_prompt_rule(nc: NegativeContext) -> str:
    """Render one compact prompt rule in single-line form."""
    do_not = nc.forbidden_pattern or nc.description
    instead = nc.canonical_alternative or "Follow established project patterns"
    sev = nc.severity.value.upper()
    return f"- [{sev}|{nc.source_signal.value}] {do_not} -> {instead}"


def _item_to_raw_payload(nc: NegativeContext) -> dict[str, object]:
    """Serialize a NegativeContext item for machine-readable export."""
    return {
        "anti_pattern_id": nc.anti_pattern_id,
        "category": nc.category.value,
        "signal": nc.source_signal.value,
        "severity": nc.severity.value,
        "scope": nc.scope.value,
        "description": nc.description,
        "forbidden_pattern": nc.forbidden_pattern,
        "canonical_alternative": nc.canonical_alternative,
        "affected_files": nc.affected_files,
        "confidence": nc.confidence,
        "rationale": nc.rationale,
    }


# ---------------------------------------------------------------------------
# Format renderers
# ---------------------------------------------------------------------------


def _render_instructions(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
) -> str:
    """Render as .instructions.md compatible format with YAML front-matter."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append("---")
    lines.append('applyTo: "**"')
    lines.append("description: >-")
    lines.append(
        "  Anti-pattern constraints from drift analysis."
        "  DO NOT reproduce these patterns in new code."
    )
    lines.append("---")
    lines.append("")

    lines.append(MARKER_BEGIN)
    lines.append("")
    lines.append("# Anti-Pattern Constraints (drift-generated)")
    lines.append("")
    lines.append(
        "> **These patterns have been detected in this repository."
        " Do NOT reproduce them in new or modified code.**"
    )
    lines.append("")

    lines.append(_render_body(items, drift_score, severity, now))

    lines.append(MARKER_END)
    lines.append("")
    return "\n".join(lines)


def _render_prompt(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
) -> str:
    """Render as compact .prompt.md format for token-efficient prompting."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    lines: list[str] = []
    lines.append("---")
    lines.append("mode: agent")
    lines.append("description: >-")
    lines.append(
        "  Anti-pattern constraints from drift analysis."
        "  Consult before generating code."
    )
    lines.append("---")
    lines.append("")

    lines.append(MARKER_BEGIN)
    lines.append("")
    lines.append("# Repository Anti-Patterns (Compact)")
    lines.append("")
    lines.append(
        "Apply these constraints while generating code."
        " Each rule is `DO_NOT -> INSTEAD`."
    )
    lines.append("")

    for item in items:
        lines.append(_render_prompt_rule(item))

    lines.append("")
    lines.append(
        f"Drift snapshot: score={drift_score:.2f}, severity={severity.value},"
        f" rules={len(items)}, generated={now}."
    )
    lines.append("")

    lines.append(MARKER_END)
    lines.append("")
    return "\n".join(lines)


def _render_raw(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
) -> str:
    """Render as machine-readable JSON for orchestration workflows."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    payload = {
        "format": "drift-negative-context-v1",
        "generated_on": now,
        "drift_score": drift_score,
        "severity": severity.value,
        "total_items": len(items),
        "items": [_item_to_raw_payload(item) for item in items],
    }
    return json.dumps(payload, indent=2)


def _render_body(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
    date: str,
) -> str:
    """Render the common body: grouped items + status footer."""
    lines: list[str] = []

    groups = _group_by_category(items)
    category_order = sorted(
        groups,
        key=lambda c: (
            0 if c == NegativeContextCategory.SECURITY else 1,
            -len(groups[c]),
        ),
    )

    for cat in category_order:
        heading = _CATEGORY_HEADING.get(cat, cat.value.title())
        lines.append(f"## {heading}")
        lines.append("")
        for item in groups[cat]:
            lines.append(_render_item(item))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        f"*Generated by drift on {date}."
        f" Drift score: {drift_score:.2f} ({severity.value})."
        f" {len(items)} anti-patterns detected.*"
    )
    lines.append("")
    return "\n".join(lines)


_RENDERERS = {
    "instructions": _render_instructions,
    "prompt": _render_prompt,
    "raw": _render_raw,
}


def render_negative_context_markdown(
    items: list[NegativeContext],
    *,
    fmt: str = "instructions",
    drift_score: float = 0.0,
    severity: Severity = Severity.INFO,
) -> str:
    """Render negative context items for the selected format."""
    renderer = _RENDERERS.get(fmt, _render_raw)

    if not items:
        return _render_empty(fmt, drift_score, severity)

    return renderer(items, drift_score, severity)


def _render_empty(
    fmt: str,
    drift_score: float,
    severity: Severity,
) -> str:
    """Render an empty-state document when no anti-patterns are found."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    if fmt == "raw":
        payload = {
            "format": "drift-negative-context-v1",
            "generated_on": now,
            "drift_score": drift_score,
            "severity": severity.value,
            "total_items": 0,
            "items": [],
        }
        return json.dumps(payload, indent=2)

    lines: list[str] = []

    if fmt == "instructions":
        lines.append("---")
        lines.append('applyTo: "**"')
        lines.append("description: >-")
        lines.append("  Anti-pattern constraints from drift analysis.")
        lines.append("---")
        lines.append("")

    if fmt == "prompt":
        lines.append("---")
        lines.append("mode: agent")
        lines.append("description: >-")
        lines.append("  Anti-pattern constraints from drift analysis.")
        lines.append("---")
        lines.append("")

    lines.append(MARKER_BEGIN)
    lines.append("")
    lines.append("# Anti-Pattern Constraints (drift-generated)")
    lines.append("")
    lines.append(
        "No significant anti-patterns detected."
        f" Drift score: {drift_score:.2f} ({severity.value})."
    )
    lines.append("")
    lines.append(f"*Generated by drift on {now}.*")
    lines.append("")
    lines.append(MARKER_END)
    lines.append("")

    return "\n".join(lines)
