"""Skill-Analyzer: Invalidierung von Guard-Skills.

Guard-Skills (``.github/skills/guard-*/SKILL.md``) binden Maintainer-Leitplanken
an Module. Wenn die Pfade, die ein Guard schützt, geändert werden, muss der
Guard inhaltlich re-validiert werden.

Scope-Resolution:

1. **Bevorzugt** ``applies_to: list[str]`` Frontmatter (ADR-087).
2. **Fallback** Ableitung aus dem Skill-Namen: ``guard-src-drift-signals``
   → ``src/drift/signals/**`` (Konvention: ``-`` → ``/``, Suffix ``/**``
   angehängt).

Nur Skills, die mit ``guard-`` beginnen, werden betrachtet — andere Skills
sind informell und außerhalb des Blast-Scopes.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from drift_engine.blast_radius._adr_frontmatter import parse_frontmatter_block
from drift_engine.blast_radius._glob import files_matching
from drift_engine.blast_radius._models import BlastImpact, BlastImpactKind, BlastSeverity

_log = logging.getLogger("drift.blast_radius.skill")

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_SKILL_NAME_RE = re.compile(r"^guard-(.+)$")


def _derive_scope_from_name(skill_name: str) -> tuple[str, ...]:
    """Konvention: ``guard-src-drift-signals`` → ``src/drift/signals/**``.

    Mehrdeutige Fälle werden konservativ behandelt (Pattern mit ``/**``).
    """
    match = _SKILL_NAME_RE.match(skill_name)
    if not match:
        return ()
    body = match.group(1)
    path = body.replace("-", "/")
    return (f"{path}/**", path)


def _parse_skill(skill_md: Path) -> tuple[str, tuple[str, ...]] | None:
    """Lade Skill-Frontmatter und ermittle (name, scope-patterns)."""
    try:
        content = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _FRONTMATTER_RE.match(content)
    raw: dict[str, object] = {}
    if match:
        raw = parse_frontmatter_block(match.group(1))
    name_val = raw.get("name")
    name = str(name_val) if isinstance(name_val, str) else skill_md.parent.name
    applies_raw = raw.get("applies_to")
    scope: tuple[str, ...]
    if isinstance(applies_raw, tuple):
        scope = tuple(str(item) for item in applies_raw if item)
    elif isinstance(applies_raw, str) and applies_raw:
        scope = (applies_raw,)
    else:
        scope = _derive_scope_from_name(name)
    return name, scope


def analyze_skill_impacts(
    repo_path: Path,
    changed_files: tuple[str, ...],
) -> tuple[list[BlastImpact], list[str]]:
    """Ermittle Guard-Skill-Invalidierungen."""
    if not changed_files:
        return [], []
    skills_dir = repo_path / ".github" / "skills"
    if not skills_dir.is_dir():
        return [], ["Kein .github/skills/-Verzeichnis — Skill-Analyse übersprungen."]

    impacts: list[BlastImpact] = []
    for skill_md in sorted(skills_dir.glob("guard-*/SKILL.md")):
        parsed = _parse_skill(skill_md)
        if parsed is None:
            continue
        name, scope_patterns = parsed
        if not scope_patterns:
            continue
        hit_pattern: str | None = None
        matched_files: tuple[str, ...] = ()
        for pattern in scope_patterns:
            candidates = files_matching(changed_files, pattern)
            if candidates:
                hit_pattern = pattern
                matched_files = candidates
                break
        if hit_pattern is None:
            continue
        rel_path = skill_md.relative_to(repo_path).as_posix()
        impacts.append(
            BlastImpact(
                kind=BlastImpactKind.SKILL,
                target_id=name,
                target_path=rel_path,
                severity=BlastSeverity.HIGH,
                reason=(
                    f"Guard-Skill {name!r} deckt geänderten Pfad via "
                    f"applies_to-Pattern {hit_pattern!r} ab und sollte re-validiert werden."
                ),
                scope_match=hit_pattern,
                matched_files=matched_files,
                requires_maintainer_ack=False,
            )
        )
    return impacts, []
