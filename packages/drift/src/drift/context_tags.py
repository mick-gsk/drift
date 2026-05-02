"""Inline context-tagging — ``# drift:context`` pragmas (ADR-006).

Context tags annotate code regions with intentional-variance semantics.
Unlike ``drift:ignore`` which *suppresses* findings, ``drift:context``
*dampens* them and records the declared intent in finding metadata.
"""

from __future__ import annotations

import re
from pathlib import Path

from drift.models import FileInfo, Finding

# Tag body: one or more comma-separated tokens (lowercase, hyphens, underscores, digits).
_TAG_BODY = r"([\w\-]+(?:\s*,\s*[\w\-]+)*)"

# Python:  # drift:context <tags>
_PY_PATTERN = re.compile(rf"#\s*drift:context\s+{_TAG_BODY}")
# JS/TS:   // drift:context <tags>
_JS_PATTERN = re.compile(rf"//\s*drift:context\s+{_TAG_BODY}")

_PATTERN_BY_LANG: dict[str, re.Pattern[str]] = {
    "python": _PY_PATTERN,
    "typescript": _JS_PATTERN,
    "tsx": _JS_PATTERN,
    "javascript": _JS_PATTERN,
    "jsx": _JS_PATTERN,
}


def _parse_tags(raw: str) -> set[str]:
    """Split a raw comma-separated tag string into a normalised set."""
    return {t.strip().lower() for t in raw.split(",") if t.strip()}


def scan_context_tags(
    files: list[FileInfo],
    repo_path: Path,
) -> dict[tuple[str, int], set[str]]:
    """Scan source files for ``drift:context`` comments.

    Returns a mapping of ``(posix_path, line_number)`` → set of tag strings.
    """
    tags: dict[tuple[str, int], set[str]] = {}

    for finfo in files:
        pattern = _PATTERN_BY_LANG.get(finfo.language)
        if pattern is None:
            continue
        full_path = repo_path / finfo.path
        try:
            text = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            m = pattern.search(line)
            if m is None:
                continue
            matched_tags = _parse_tags(m.group(1))
            if matched_tags:
                tags[(finfo.path.as_posix(), line_no)] = matched_tags

    return tags


def apply_context_tags(
    findings: list[Finding],
    context_tags: dict[tuple[str, int], set[str]],
    dampening: float = 0.5,
) -> tuple[list[Finding], int]:
    """Annotate findings with context tags and dampen their scores.

    Findings whose ``[start_line, end_line]`` range overlaps a context-tagged
    line receive:
    - ``metadata["context_tags"]`` — the union of overlapping tags
    - ``score *= dampening`` — score reduction (then ``impact`` is recomputed
      externally after this step)

    Returns ``(all_findings, context_tagged_count)``.
    """
    if not context_tags:
        return findings, 0

    dampening = max(0.0, min(1.0, dampening))
    tagged_count = 0

    for f in findings:
        if f.file_path is None or f.start_line is None:
            continue

        end_line = f.end_line if f.end_line is not None else f.start_line
        start_line = min(f.start_line, end_line)
        end_line = max(f.start_line, end_line)

        merged_tags: set[str] = set()
        for line_no in range(start_line, end_line + 1):
            key = (f.file_path.as_posix(), line_no)
            entry = context_tags.get(key)
            if entry is not None:
                merged_tags |= entry

        if merged_tags:
            f.metadata["context_tags"] = sorted(merged_tags)
            f.score = round(f.score * dampening, 4)
            tagged_count += 1

    return findings, tagged_count
