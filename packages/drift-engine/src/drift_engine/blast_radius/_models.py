"""Immutable Pydantic-Modelle für die Blast-Radius-Engine (ADR-087).

Alle Modelle sind ``frozen=True`` mit ``extra="forbid"``, damit Reports
deterministisch serialisierbar sind und keine stillen Schema-Drifts
entstehen können.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: int = 1
"""Report-Schema-Version. Bei Breaking-Changes inkrementieren."""


class BlastSeverity(StrEnum):
    """Geschlossenes Severity-Set für ``BlastImpact``.

    - ``critical``: Invalidiert eine Policy-/ADR-Einheit, die ohne Maintainer-Ack
      nicht gepusht werden darf.
    - ``high``: Strukturelle Invalidierung mit Pflicht-Review (z. B. Guard-Skill).
    - ``medium``: Abgeleitete Abhängigkeitsbrüche, sollten verifiziert werden.
    - ``low``: Nur Kontext / Information.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BlastImpactKind(StrEnum):
    """Typ einer Invalidierung."""

    ARCH_DEPENDENCY = "arch_dependency"
    ADR = "adr"
    SKILL = "skill"
    POLICY = "policy"


class BlastTrigger(BaseModel):
    """Der auslösende Diff oder Änderungsumfang."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ref: str = Field(
        default="HEAD",
        description="Git-Basis-Ref für den Diff (z. B. 'HEAD~1' oder 'origin/main').",
    )
    head: str = Field(
        default="HEAD",
        description="Git-HEAD oder Worktree-Marker, gegen den verglichen wird.",
    )
    head_sha: str | None = Field(
        default=None,
        description="Aufgelöster Commit-SHA von ``head``, falls verfügbar.",
    )
    changed_files: tuple[str, ...] = Field(
        default_factory=tuple,
        description="POSIX-relative Pfade der geänderten Dateien.",
    )


class BlastImpact(BaseModel):
    """Eine einzelne Invalidierung durch einen Trigger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: BlastImpactKind
    target_id: str = Field(
        description=(
            "Stabile Identität des invalidierten Artefakts. "
            "ADR-ID für ADRs, Skill-Name für Skills, Modul-Pfad für Arch, "
            "Gate-ID für Policy."
        ),
    )
    target_path: str | None = Field(
        default=None,
        description="Dateipfad des invalidierten Artefakts, falls anwendbar.",
    )
    severity: BlastSeverity
    reason: str = Field(
        description="Kurzbegründung in einem Satz, warum dieses Artefakt invalidiert wird.",
    )
    scope_match: str | None = Field(
        default=None,
        description="Pattern oder Token, das den Match ausgelöst hat (z. B. Glob).",
    )
    matched_files: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Untermenge von ``changed_files``, die diesen Impact erklärt.",
    )
    requires_maintainer_ack: bool = Field(
        default=False,
        description=(
            "True, wenn dieser Impact ohne Maintainer-Ack in "
            "``blast_reports/acks/`` nicht gepusht werden darf."
        ),
    )


class BlastReport(BaseModel):
    """Ergebnis einer Blast-Radius-Analyse."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_v: int = Field(default=SCHEMA_VERSION, description="Report-Schema-Version.")
    generated_at: str = Field(
        description="ISO-8601-Timestamp (UTC) der Report-Erzeugung.",
    )
    drift_version: str = Field(description="drift-analyzer Version zur Laufzeit.")
    trigger: BlastTrigger
    impacts: tuple[BlastImpact, ...] = Field(default_factory=tuple)
    recommendations: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Handlungsempfehlungen in Lesereihenfolge.",
    )
    degraded: bool = Field(
        default=False,
        description=(
            "True, wenn ein Analyzer wegen Timeout/Fehler nur teilweise "
            "gelaufen ist. Das Gate blockiert bei ``degraded=True`` nicht hart."
        ),
    )
    degradation_notes: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Menschenlesbare Gründe, warum der Report degradiert ist.",
    )
    generated_by: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Reproduzierbarkeits-Block: git_sha, script, timestamp. "
            "Analog zu Feature-Evidence-Artefakten."
        ),
    )

    def has_critical_impacts(self) -> bool:
        """True, wenn mindestens ein Impact harte Maintainer-Ack erfordert."""
        return any(impact.requires_maintainer_ack for impact in self.impacts)

    def critical_impact_ids(self) -> tuple[str, ...]:
        """Stabile Liste der target_ids, die Ack verlangen — sortiert für Determinismus."""
        ids = {impact.target_id for impact in self.impacts if impact.requires_maintainer_ack}
        return tuple(sorted(ids))
