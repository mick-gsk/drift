"""Render negative context items as Markdown for agent consumption.

Supports three output formats:
- ``instructions``: compatible with ``.instructions.md`` / copilot-instructions
- ``prompt``: compatible with ``.prompt.md`` (system prompt style)
- ``raw``: plain Markdown without YAML front-matter or markers
"""

from __future__ import annotations

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

    # Forbidden pattern
    if nc.forbidden_pattern:
        lines.append(f"  - **DO NOT:** {nc.forbidden_pattern}")

    # Canonical alternative
    if nc.canonical_alternative:
        lines.append(f"  - **INSTEAD:** {nc.canonical_alternative}")

    # Affected files (max 5)
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

    # YAML front-matter
    lines.append("---")
    lines.append('applyTo: "**"')
    lines.append(
        "description: >-"
    )
    lines.append(
        "  Anti-pattern constraints from drift analysis."
        "  DO NOT reproduce these patterns in new code."
    )
    lines.append("---")
    lines.append("")

    # Content
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
    """Render as .prompt.md compatible format (system-prompt style)."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    lines: list[str] = []

    lines.append("---")
    lines.append("mode: agent")
    lines.append(
        "description: >-"
    )
    lines.append(
        "  Anti-pattern constraints from drift analysis."
        "  Consult before generating code."
    )
    lines.append("---")
    lines.append("")

    lines.append(MARKER_BEGIN)
    lines.append("")
    lines.append("# Repository Anti-Patterns")
    lines.append("")
    lines.append(
        "Before generating code, review these known anti-patterns."
        " Each one has been detected by static analysis."
        " Reproducing them degrades architectural coherence."
    )
    lines.append("")

    lines.append(_render_body(items, drift_score, severity, now))

    lines.append(MARKER_END)
    lines.append("")

    return "\n".join(lines)


def _render_raw(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
) -> str:
    """Render as plain Markdown without front-matter."""
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d")

    lines: list[str] = []

    lines.append(MARKER_BEGIN)
    lines.append("")
    lines.append("# Anti-Pattern Constraints")
    lines.append("")

    lines.append(_render_body(items, drift_score, severity, now))

    lines.append(MARKER_END)
    lines.append("")

    return "\n".join(lines)


def _render_body(
    items: list[NegativeContext],
    drift_score: float,
    severity: Severity,
    date: str,
) -> str:
    """Render the common body: grouped items + status footer."""
    lines: list[str] = []

    groups = _group_by_category(items)

    # Category order: security first, then by item count
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

    # Status footer
    lines.append("---")
    lines.append("")
    lines.append(
        f"*Generated by drift on {date}."
        f" Drift score: {drift_score:.2f} ({severity.value})."
        f" {len(items)} anti-patterns detected.*"
    )
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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
    """Render negative context items as Markdown.

    Parameters
    ----------
    items:
        NegativeContext items, typically from findings_to_negative_context().
    fmt:
        Output format: "instructions", "prompt", or "raw".
    drift_score:
        Current drift score for the status footer.
    severity:
        Current overall severity for the status footer.
    """
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
    lines: list[str] = []

    if fmt == "instructions":
        lines.append("---")
        lines.append('applyTo: "**"')
        lines.append(
            "description: >-"
        )
        lines.append(
            "  Anti-pattern constraints from drift analysis."
        )
        lines.append("---")
        lines.append("")

    if fmt == "prompt":
        lines.append("---")
        lines.append("mode: agent")
        lines.append(
            "description: >-"
        )
        lines.append(
            "  Anti-pattern constraints from drift analysis."
        )
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
    lines.append(
        f"*Generated by drift on {now}.*"
    )
    lines.append("")
    lines.append(MARKER_END)
    lines.append("")

    return "\n".join(lines)
