"""Rendering primitives for help navigation sections."""

from __future__ import annotations

from drift_cli.help_nav._models import HelpSection


def _cap_line(line: str, width: int) -> str:
    if width < 44:
        limit = 48
    elif width < 66:
        limit = 68
    else:
        limit = max(width - 8, 72)
    if len(line) <= limit:
        return line
    if limit <= 3:
        return line[:limit]
    return f"{line[: limit - 3].rstrip()}..."


def render_help_section_rows(section: HelpSection, width: int) -> list[tuple[str, str]]:
    """Convert a help section into Click definition-list rows."""
    if not section.body_lines:
        return []

    rows: list[tuple[str, str]] = []
    first_line = _cap_line(section.body_lines[0], width)
    rows.append(("", first_line))

    for line in section.body_lines[1:]:
        rows.append(("", _cap_line(line, width)))

    if section.next_hint:
        rows.append(("", _cap_line(f"Next: {section.next_hint}", width)))

    return rows
