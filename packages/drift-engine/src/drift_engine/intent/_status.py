"""Intent status rendering — human-readable requirement status lines."""

from __future__ import annotations

from drift_engine.intent._matcher import RequirementStatus


def format_intent_status(statuses: list[RequirementStatus]) -> list[str]:
    """Format requirement statuses as human-readable lines.

    Parameters
    ----------
    statuses:
        Requirement statuses from ``match_findings_to_contracts()``.

    Returns
    -------
    list[str]
        One or more lines per requirement with ✅/❌ prefix.
    """
    lines: list[str] = []

    for s in statuses:
        if s.satisfied:
            lines.append(f"✅ {s.description_plain}")
        else:
            count = len(s.violated_by)
            lines.append(
                f"❌ {s.description_plain} — {count} Problem{'e' if count != 1 else ''} gefunden"
            )
            # Show affected files (deduplicated)
            seen_files: set[str] = set()
            for f in s.violated_by:
                if f.file_path and str(f.file_path) not in seen_files:
                    seen_files.add(str(f.file_path))
                    lines.append(f"   ↳ {f.file_path}: {f.title}")

    return lines
