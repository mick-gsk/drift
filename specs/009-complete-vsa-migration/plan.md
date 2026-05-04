# Implementation Plan: Complete VSA Migration

**Branch**: `feat/adr100-phase7a-cleanup` | **Date**: 2026-05-02 | **Spec**: [specs/009-complete-vsa-migration/spec.md](specs/009-complete-vsa-migration/spec.md)
**Input**: Feature specification from `specs/009-complete-vsa-migration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Die Monorepo-Migration wird finalisiert, indem aktive Implementierungen unter `src/drift` vollstaendig zugunsten kanonischer Capability-Pakete (`packages/drift-*`) abgeloest werden. Der Plan kombiniert Importnormalisierung, klare Paketgrenzen, dokumentierten Abschlussstatus und Gate-basierte Verifikation, damit Contributor und Agenten nur noch einen eindeutigen Implementierungspfad pro Capability sehen.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click, Pydantic, Rich, pytest, mypy, ruff  
**Storage**: N/A (Code- und Importstrukturmigration)  
**Testing**: pytest, static import audits, `make check`, `make gate-check COMMIT_TYPE=feat`, migrationsspezifische Audit-Skripte  
**Target Platform**: Cross-platform Entwickler- und CI-Workflows (Windows/Linux/macOS)
**Project Type**: Monorepo mit Python Capability-Paketen und CLI/Ouput/Engine-Slices  
**Performance Goals**: Keine regressionsbedingte Verschlechterung gegen bestehende Perf-Budgets; Migrationsverifikation bleibt im normalen Gate-Fenster lauffaehig  
**Constraints**: Keine funktionalen Breaking Changes bei oeffentlichen Entry-Points; keine parallelen aktiven Implementierungspfade fuer dieselbe Capability  
**Scale/Scope**: Repository-weite Konsolidierung fuer alle verbleibenden Legacy-Pfade in `src/drift`

## Constitution Check

*GATE: Partially blocked; Governance-Klaerung vor Implementierungsstart erforderlich.*

### Pre-Research Gate

- [ ] **I. Library-First**: Offen bis Governance-Entscheidung dokumentiert ist, ob Capability-Pakete die bestehenden `src/drift`-Slice-Vorgaben formal abloesen.
- [ ] **II. Test-First**: Offen bis explizite RED-Tasks je User Story mit zuerst scheiternden Tests im Tasks-Artefakt verankert sind.
- [x] **III. Functional Programming**: Migration veraendert primaer Modulgrenzen und Importe; Side Effects bleiben an CLI/IO-Grenzen isoliert.
- [x] **IV. CLI Interface & Observability**: Bestehende CLI-/Output-Vertraege bleiben erhalten (JSON + Rich) und werden als Regressionkriterium verifiziert.
- [x] **V. Simplicity & YAGNI**: Kein neues Framework oder neues Laufzeitmodell; nur strukturell noetige Konsolidierung.
- [ ] **VI. Vertical Slices**: Offen bis Constitution oder Migrationsziel formal harmonisiert ist (Capability-Paketgrenzen vs. `src/drift/<feature_name>`-Vorgabe).

**Gate-Entscheidung**: Keine Implementierung vor dokumentierter Governance-Klaerung fuer I/VI und RED-Test-Nachweis fuer II.

### Post-Design Re-Check

- [ ] Governance-Artefakte fuer I/VI sind vor Implementierung explizit zu beschliessen und zu dokumentieren.
- [x] Datenmodell und Contract beschreiben klare Abschlusskriterien (kein aktiver Legacy-Pfad, erfolgreiche Gates, dokumentierter Zielzustand).
- [x] Quickstart priorisiert schrittweise Verifikation statt Big-Bang-Risiko.
- [ ] RED-Testpflicht je Story ist im Tasks-Artefakt vor Umsetzungsstart vollstaendig nachzuweisen.

## Project Structure

### Documentation (this feature)

```text
specs/009-complete-vsa-migration/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── migration-boundary.contract.md
└── tasks.md
```

### Source Code (repository root)
```text
packages/
├── drift/
├── drift-cli/
├── drift-config/
├── drift-engine/
├── drift-mcp/
├── drift-output/
├── drift-sdk/
├── drift-session/
└── drift-verify/

src/
└── drift/            # wird im Zielzustand nicht mehr als aktive Implementierungsquelle genutzt

tests/
├── ...               # bestehende suites + migration/contract checks
```

**Structure Decision**: Vertikale Capability-Paketstruktur ist verbindlich. Die Migration konsolidiert aktive Implementierung auf `packages/drift-*`; `src/drift` wird als produktive Quelle eliminiert. Validierung erfolgt ueber Import-Audits, Contract-Tests und bestehende Repo-Gates.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution I/VI vs. Capability-Paket-Zielbild | Die Migration zielt auf kanonische `packages/drift-*`-Pfade statt neuer Slices unter `src/drift/`. | Rueckkehr zu `src/drift`-zentrierter Slice-Implementierung konterkariert das definierte Migrationsziel und erhoeht Dual-Ownership-Risiken. |
| Constitution II (Test-First) nicht explizit per Story-RED belegt | Architekturmigration braucht storyspezifische, zuerst scheiternde Nachweise fuer sichere Umstellung. | Reine Abschluss-Checks ohne fruehe RED-Tests erkennen Fehlzuordnungen erst spaet und erhoehen Rework-Risiko. |
