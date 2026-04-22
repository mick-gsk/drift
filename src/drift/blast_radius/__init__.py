"""Blast-Radius-Engine (K1) — transitive Invalidierungsanalyse vor strukturellen Edits.

Siehe ADR-087. Das Paket liefert:

- ``BlastReport`` / ``BlastImpact`` Pydantic-Modelle (immutable).
- Vier Analyzer: Arch (Modul-Dependencies), ADR (Scope-Invalidierung),
  Skill (Guard-Skill-Invalidierung), Policy (Gate-Trigger §7/§18).
- ``compute_blast_report()`` als orchestrierender Entry-Point.
- Persistence via ``save_blast_report()`` in ``blast_reports/``.

Agent-Boundary: Dieses Paket berechnet und persistiert Reports. Es schreibt
**keine** Ack-Dateien unter ``blast_reports/acks/`` — das ist Maintainer-Domäne.
"""

from __future__ import annotations

from drift.blast_radius._models import (
    BlastImpact,
    BlastImpactKind,
    BlastReport,
    BlastSeverity,
    BlastTrigger,
)
from drift.blast_radius._persistence import (
    blast_reports_dir,
    load_blast_report,
    save_blast_report,
)
from drift.blast_radius.engine import compute_blast_report

__all__ = [
    "BlastImpact",
    "BlastImpactKind",
    "BlastReport",
    "BlastSeverity",
    "BlastTrigger",
    "blast_reports_dir",
    "compute_blast_report",
    "load_blast_report",
    "save_blast_report",
]
