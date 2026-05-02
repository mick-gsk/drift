# Implementation Plan: 006 Human Decision Cockpit

**Branch**: `010-before-specify-hook` | **Date**: 2026-05-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-human-decision-cockpit/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Drift erhaelt ein neues Cockpit-Slice, das pro Pull Request eine entscheidungsfertige Governance-Ansicht erzeugt: genau ein Decision Status (Go / Go with Guardrails / No-Go), Top-Risikotreiber, Minimal Safe Change Set, Accountability Cluster und ein versioniertes Decision Ledger mit 7/30-Tage-Outcomes. Die Architektur trennt deterministische Entscheidungsermittlung (Library-First) von UI-Rendering und erzwingt nachvollziehbare Human Overrides mit Pflicht-Begruendung.

## Technical Context

**Language/Version**: Python 3.11+ (Decision Engine), TypeScript 5.x + React 18 (Cockpit UI)  
**Primary Dependencies**: Click, Pydantic, Rich, drift-engine/drift-output APIs; React, Vite, Vitest fuer Frontend  
**Storage**: Repository-lokale Artefakte unter `.drift/cockpit/` (JSON) plus append-only Ledger-Datei  
**Testing**: pytest (unit/contract/integration), Vitest + Testing Library (UI), mypy, ruff  
**Target Platform**: Lokale Maintainer-Workstations und CI Artefakt-Viewer (Browser)  
**Project Type**: Vertical Slice + Web UI (library/cli + web app)  
**Performance Goals**: Vollstaendiges Decision Panel in <= 120 Sekunden pro PR (SC-001), Cockpit-Render < 2s aus vorhandenen Artefakten  
**Constraints**: Genau ein aktiver Status pro PR; fehlende Evidenz erzwingt No-Go; deterministische Status-Schwellen; Konfliktauflosung bei Parallel-Edits  
**Scale/Scope**: Initial 1 Cockpit-Ansicht pro PR, 7/30-Tage Outcome-Tracking fuer mindestens 90% der entschiedenen PRs (SC-004)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify each principle from `.specify/memory/constitution.md` (v1.1.0):

- [x] **I. Library-First**: Kernlogik liegt in `src/drift/decision_cockpit/`; CLI/UI sind Adapter ohne Entscheidungslogik.
- [x] **II. Test-First**: RED-Tests fuer Statusmapping, Minimal-Safe-Berechnung, Ledger-Versionierung und Override-Regeln werden vor Implementierung geschrieben.
- [x] **III. Functional Programming**: Entscheidungspfade als pure functions; Pydantic Modelle frozen; I/O an Artefakt- und CLI-Grenzen isoliert.
- [x] **IV. CLI Interface & Observability**: Neues Click-Subcommand liefert JSON + Rich; strukturierte Cockpit-Metadaten fuer PR/Status/Latency.
- [x] **V. Simplicity & YAGNI**: V1 fokussiert auf PR-Entscheidung und Ledger, keine Multi-Repo-Administration oder Rollensystem.
- [x] **VI. Vertical Slices**: Eigenes Slice `src/drift/decision_cockpit/` mit Modellen, Core-Logik, Output und Command; keine sibling-internals.

## Project Structure

### Documentation (this feature)

```text
specs/006-human-decision-cockpit/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cockpit-api.yaml
│   └── ledger-event-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
src/drift/decision_cockpit/
├── __init__.py                 # Public API: build_decision_bundle(...)
├── _models.py                  # Frozen decision/ledger/cluster models
├── _status_engine.py           # Deterministische Statuslogik + Schwellen
├── _safe_plan.py               # Minimal Safe Change Set Berechnung
├── _cluster.py                 # Accountability Cluster Aggregation
├── _ledger.py                  # Ledger write/read + optimistic locking
├── _output.py                  # JSON + Rich projection
└── _cmd.py                     # Click: drift cockpit build/view

playground/src/cockpit/
├── CockpitApp.tsx              # Decision Panel + Safe Plan + Graph + Ledger
├── api.ts                      # Typed contract client fuer cockpit-api.yaml
├── components/
└── test/

tests/decision_cockpit/
├── test_status_engine.py
├── test_safe_plan.py
├── test_ledger_contract.py
├── test_cockpit_cmd_integration.py
└── test_cockpit_threshold_boundaries.py
```

**Structure Decision**: Vertical Slice fuer Governance-Logik in `src/drift/decision_cockpit/` plus UI-Adapter in `playground/src/cockpit/`. So bleibt die Entscheidungslogik testbar und CLI-faehig, waehrend die Web-App auf stabilen Contracts aufsetzt.

## Phase 0 Research (resolved)

- Status-Schwellen werden statusspezifisch und deterministisch definiert; Grenzwerte mappen auf genau einen Status.
- Unzureichende Evidenz setzt zwingend No-Go bis Evidenznachlieferung.
- Human Override ist erlaubt, aber nur mit Pflicht-Begruendung im Ledger.
- Fehlende Outcomes werden als `pending` modelliert, nicht als neutral/negativ.
- Gleichzeitige Aenderungen nutzen optimistic locking (`version`) mit expliziter Konfliktaufloesung.

## Phase 1 Design Outputs

- `data-model.md`: Alle Cockpit-Entitaeten, Beziehungen und Zustandsuebergaenge.
- `contracts/cockpit-api.yaml`: PR-zentrierte REST/JSON Contracts fuer Panel, Safe Plan, Ledger und Outcome-Update.
- `contracts/ledger-event-contract.md`: Auditierbare Events inkl. Override-Pflichtfelder und Konfliktregeln.
- `quickstart.md`: End-to-end local flow (Build artefacts -> UI -> Decision -> Outcome).

## Post-Design Constitution Re-check

- [x] Library-First weiterhin erfuellt: API/CLI nutzen `decision_cockpit` Public API.
- [x] Test-First vorbereitet: explizite Testmodule fuer jede Kernregel benannt.
- [x] Functional rule bleibt erfuellt: Optimistic locking und Statusmapping sind side-effect-arm modelliert.
- [x] CLI/Observability erfuellt: `drift cockpit` plus JSON/Rich Contract vorgesehen.
- [x] Simplicity erfuellt: Kein RBAC, kein Multi-tenant, kein Runtime-ML in V1.
- [x] Vertical Slices erfuellt: Cross-slice Imports nur ueber oeffentliche Drift APIs.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| UI ausserhalb `src/drift/` (`playground/src/cockpit/`) | Web-App ist expliziter Produktbestandteil mit eigener Laufzeit | Reines Rich/CLI-Output erfuellt den Web-App-Kern-Use-Case nicht |
| Optimistic-locking Konfliktpfad | FR-015 verlangt explizite Konfliktaufloesung bei Parallel-Edits | Last-write-wins verletzt Nachvollziehbarkeit und Audit-Sicherheit |
