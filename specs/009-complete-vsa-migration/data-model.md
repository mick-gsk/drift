# Data Model: Complete VSA Migration

## Entity: CapabilityPackage
- Purpose: Kapselt eine vertikale Drift-Funktionalitaet als kanonische Implementierungseinheit.
- Fields:
  - `name` (str): Paketname, z. B. `drift-cli`, `drift-engine`.
  - `canonical_root` (str): Quellwurzel des Pakets (z. B. `packages/drift-cli/src/drift_cli`).
  - `owned_capabilities` (list[str]): Fachliche Verantwortlichkeiten des Pakets.
  - `public_api_surfaces` (list[str]): Exportierte API-Pfade/Module.

## Entity: LegacyPath
- Purpose: Repräsentiert historische Pfade unter `src/drift`, die waehrend Migration entfernt, ersetzt oder neutralisiert werden.
- Fields:
  - `path` (str): Konkreter Legacy-Pfad.
  - `legacy_role` (enum): `implementation`, `compat_stub`, `doc_only`.
  - `status` (enum): `present`, `removed`, `redirected`.
  - `replacement_target` (str | null): Kanonischer Capability-Pfad bei Umleitung.

## Entity: ImportMapping
- Purpose: Beschreibt die Normalisierung eines internen Imports auf den kanonischen Paketpfad.
- Fields:
  - `source_import` (str): Vorheriger Importpfad.
  - `target_import` (str): Neuer kanonischer Importpfad.
  - `kind` (enum): `runtime`, `typecheck`, `test`.
  - `validated_by` (list[str]): Verifikationsschritte/Gates, die den Mapping-Status absichern.

## Entity: MigrationCompletionStatus
- Purpose: Prüft den Repository-Zielzustand fuer den Monorepo-Migrationsabschluss.
- Fields:
  - `active_legacy_impl_count` (int): Anzahl verbleibender aktiver Implementierungen unter `src/drift`.
  - `import_drift_violations` (int): Anzahl interner Importverstoesse gegen kanonische Paketpfade.
  - `quality_gate_result` (enum): `pass`, `fail`.
  - `documentation_synced` (bool): Paketgrenzen und Abschlussstatus sind in Doku aktualisiert.
  - `completed_at` (date | null): Zeitpunkt des Abschlusses.

## Relationships
- `CapabilityPackage` owns many `ImportMapping` records.
- `LegacyPath` may map to one `CapabilityPackage` via `replacement_target`.
- `MigrationCompletionStatus` aggregates all `LegacyPath` and `ImportMapping` outcomes.

## Validation Rules
- `active_legacy_impl_count` MUST be `0` for completion.
- `import_drift_violations` MUST be `0` for completion.
- `quality_gate_result` MUST be `pass` for completion.
- `documentation_synced` MUST be `true` before completion is declared.

## State Transitions
- `MigrationCompletionStatus`: `in_progress` -> `verification` -> `completed`
- Transition to `completed` is allowed only if all validation rules pass.
