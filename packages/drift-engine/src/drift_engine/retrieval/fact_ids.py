"""Fact-ID generators and migration registry (ADR-091).

Fact-IDs are **structured** and human-readable to make citations like
``gemaess POLICY#S8.p3`` reviewable. When a source document is
restructured and an ID must change, an append-only JSONL registry
redirects the old ID to the new one; ``drift_cite`` resolves transitively.

The registry path is ``decisions/fact_id_migrations.jsonl`` relative to
the repository root.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_INVALID_FRAGMENT = re.compile(r"[^A-Za-z0-9._-]+")

# --- ID generators ---------------------------------------------------------


def _slugify(fragment: str) -> str:
    """Collapse a free-form text fragment to a safe Fact-ID component."""
    normalised = _INVALID_FRAGMENT.sub("-", fragment.strip()).strip("-")
    return normalised or "unnamed"


def generate_policy_id(section: int | str, paragraph: int | str) -> str:
    """Return the Fact-ID for a POLICY.md paragraph, e.g. ``POLICY#S8.p3``."""
    return f"POLICY#S{section}.p{paragraph}"


def generate_roadmap_id(section: int | str, paragraph: int | str) -> str:
    """Return the Fact-ID for a ROADMAP.md paragraph."""
    return f"ROADMAP#S{section}.p{paragraph}"


def generate_adr_id(number: int | str, section: str) -> str:
    """Return the Fact-ID for an ADR section, e.g. ``ADR-091#decision``."""
    n = str(number).lstrip("0") or "0"
    return f"ADR-{int(n):03d}#{_slugify(section).lower()}"


def generate_audit_id(file_stem: str, row_id: str) -> str:
    """Return the Fact-ID for an audit table row, e.g. ``AUDIT/fmea_matrix#R12``."""
    return f"AUDIT/{_slugify(file_stem)}#{_slugify(row_id)}"


def generate_signal_id(signal_id: str, field: str) -> str:
    """Return the Fact-ID for a signal docstring field.

    ``field`` is one of ``rationale``, ``reason``, ``fix``, ``weight``,
    ``scope``.
    """
    return f"SIGNAL/{_slugify(signal_id)}#{_slugify(field).lower()}"


def generate_evidence_id(version: str, key: str) -> str:
    """Return the Fact-ID for a benchmark-evidence entry."""
    return f"EVIDENCE/v{_slugify(version).lstrip('v')}#{_slugify(key)}"


# --- Migration registry ----------------------------------------------------


class MigrationRegistry:
    """Append-only resolver for legacy Fact-IDs.

    The registry is a JSONL file. Non-migration metadata lines
    (``schema_version``, ``note``) are skipped. Each migration line is
    ``{"old_id": str, "new_id": str, "reason": str, "migrated_at": str}``.

    The resolver follows ``old_id -> new_id`` chains transitively with
    cycle detection to guarantee termination.
    """

    def __init__(self, entries: dict[str, str]) -> None:
        self._entries = dict(entries)

    @classmethod
    def from_file(cls, path: Path) -> MigrationRegistry:
        """Load a registry from a JSONL file. Missing file yields an empty registry."""
        entries: dict[str, str] = {}
        if not path.exists():
            return cls(entries)
        for raw in path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(record, dict):
                continue
            old_id = record.get("old_id")
            new_id = record.get("new_id")
            if isinstance(old_id, str) and isinstance(new_id, str):
                entries[old_id] = new_id
        return cls(entries)

    def resolve(self, fact_id: str) -> str:
        """Return the current Fact-ID, following migration chains.

        Breaks on cycles and returns the last non-cyclic hop.
        """
        seen: set[str] = set()
        current = fact_id
        while current in self._entries and current not in seen:
            seen.add(current)
            current = self._entries[current]
        return current

    def is_migrated(self, fact_id: str) -> bool:
        """Return True when ``fact_id`` has been superseded by a newer ID."""
        return fact_id in self._entries

    def __len__(self) -> int:
        return len(self._entries)
