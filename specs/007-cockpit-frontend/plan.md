# Implementation Plan: Drift Cockpit Frontend

**Branch**: `011-cockpit-frontend` | **Date**: 2026-05-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-cockpit-frontend/spec.md`

## Summary

Das Cockpit-Frontend ist eine Next.js-Web-App (`packages/cockpit-ui/`) mit Static Export, die die bestehende Cockpit-Backend-API (`packages/drift-cockpit/`) über konfigurierbare REST-Endpunkte konsumiert. Die App zeigt pro PR einen Decision Panel (Status, Konfidenz, Risikotreiber), Minimal-Safe-Plan-Karten mit abhakbaren Guardrails, einen Accountability-Graph und ein Decision Ledger. `drift cockpit serve` wird um ein `serve`-Subcommand erweitert, das die vorgebauten statischen Assets via FastAPI ausliefert — ohne externe Hosting-Infrastruktur.

## Technical Context

**Language/Version**: TypeScript 5.x + React 18 (Next.js 14, static export); Python 3.11+ (serve command)  
**Primary Dependencies**: Next.js 14, React 18, Tailwind CSS, Vitest + Testing Library, Playwright; FastAPI + uvicorn (Python serve)  
**Storage**: N/A (stateless UI; alle Daten via REST-API; Assets als Python-Package-Data)  
**Testing**: Vitest + Testing Library (Komponenten), Playwright (E2E), pytest (Python serve command)  
**Target Platform**: Desktop-Browser ≥1024px; lokal ausgeliefert via `drift cockpit serve`  
**Project Type**: SSR-at-build-time Static Web App + Python CLI-Erweiterung  
**Performance Goals**: Decision Panel vollständig in <2 s; Accountability Graph für 50 Cluster in <300 ms  
**Constraints**: `COCKPIT_API_URL` konfigurierbar; kein Auth in v1; kein Node.js auf Maintainer-Maschinen zur Laufzeit; Mobile out-of-scope  
**Scale/Scope**: 5 Hauptansichten (Panel, Safe Plan, Graph, Decision Form, Ledger); Desktop-only v1

## Constitution Check

*GATE: Pre-Phase-0 check — passed. Post-Phase-1 re-check — passed.*

- [x] **I. Library-First**: Die Python-Erweiterung (`drift cockpit serve`) ist ein dünner CLI-Adapter; Serving-Logik liegt in `drift_cockpit._serve` (neues Modul im bestehenden Slice). Keine Kernlogik im Click-Handler selbst.
- [x] **II. Test-First**: Vitest-Komponenten-Tests und Playwright-E2E-Tests werden vor Implementierung geschrieben (RED-Phase). Python-Tests für `serve`-Command in `tests/decision_cockpit/test_cockpit_serve_cmd.py` ebenfalls zuerst.
- [x] **III. Functional Programming**: React-Komponenten sind pure functional components; State via Hooks/Context ohne shared mutable state. Python-Serve-Modul ist zustandslos; I/O isoliert auf Startup/Request-Handler.
- [x] **IV. CLI Interface & Observability**: `drift cockpit serve --port --api-url` ist ein Click-Subcommand. Startup-Info via Rich (`console.print`); Fehler auf stderr. JSON-Output nicht zutreffend für einen Server-Start-Befehl — Begründung: kein Analyse-Output.
- [x] **V. Simplicity & YAGNI**: Kein Auth, kein Mobile, kein Multi-Repo-Admin in v1. FastAPI-Wahl über `http.server` durch konkrete Anforderung (POST/PATCH für Ledger). No speculative features.
- [x] **VI. Vertical Slices**: Frontend-Package `packages/cockpit-ui/` ist eigenständig. Python-Erweiterung bleibt im bestehenden Slice `packages/drift-cockpit/`; neues Modul `_serve.py` importiert keine Sibling-Internals.

## Project Structure

### Documentation (this feature)

```text
specs/007-cockpit-frontend/
├── plan.md                          # This file
├── research.md                      # Phase 0 output
├── data-model.md                    # Phase 1 output
├── quickstart.md                    # Phase 1 output
├── contracts/
│   └── frontend-api-contract.md    # Phase 1 output
└── tasks.md                         # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
packages/cockpit-ui/                           # NEW — Next.js static-export app
├── package.json
├── next.config.js                             # output: 'export', COCKPIT_API_URL injection
├── tsconfig.json
├── src/
│   ├── app/
│   │   └── cockpit/
│   │       └── [owner]/[repo]/[pr_number]/
│   │           └── page.tsx                   # Main cockpit page (SSR at build time)
│   ├── components/
│   │   ├── DecisionPanel/                     # Status badge + confidence + risk drivers
│   │   ├── MinimalSafePlanCard/               # Plan card + guardrail checklist
│   │   ├── AccountabilityGraph/               # Risk cluster visualisation
│   │   ├── DecisionForm/                      # Human decision form
│   │   └── LedgerTimeline/                    # Ledger entry timeline
│   ├── api/
│   │   └── client.ts                          # Typed REST client (COCKPIT_API_URL)
│   ├── hooks/
│   │   ├── useDecisionPanel.ts                # Polling + panel state
│   │   └── useScanStatus.ts                   # 3s poll for running scans
│   └── types/
│       └── cockpit.ts                         # TypeScript types from data-model.md
├── tests/
│   ├── components/                            # Vitest + Testing Library
│   └── e2e/                                   # Playwright E2E
└── out/                                       # Build output (gitignored)

packages/drift-cockpit/src/drift_cockpit/
├── _serve.py                                  # NEW — FastAPI app + static file serving
└── _cmd.py                                    # EXTENDED — add `serve` subcommand

tests/decision_cockpit/
└── test_cockpit_serve_cmd.py                  # NEW — pytest for serve command
```

**Structure Decision**: Eigenständiges Next.js-Package `packages/cockpit-ui/` für vollständige Frontend-Unabhängigkeit. Python-Erweiterung bleibt im bestehenden `drift-cockpit`-Slice, da sie nur einen CLI-Adapter und einen Serving-Adapter hinzufügt — keine neue Geschäftslogik.

## Complexity Tracking

| Entscheidung | Warum notwendig | Einfachere Alternative verworfen weil |
|---|---|---|
| FastAPI statt `http.server` | POST/PATCH für Ledger-Updates + statische Files in einem Prozess | `http.server` unterstützt kein POST/PATCH nativ ohne Boilerplate-Handler |
| Next.js `output: 'export'` statt SSR-Runtime | Python liefert statische Assets; kein Node.js zur Laufzeit | SSR-Runtime erfordert Node.js auf Maintainer-Maschinen — out-of-scope |
| Polling statt SSE/WebSocket | Static Export unterstützt keine persistenten Server-Verbindungen | SSE/WebSocket benötigen Server-Push-Infrastruktur, die Static Export nicht bietet |

## Phase 0 Research (resolved)

Alle Unklarheiten aufgelöst in [research.md](research.md):

- PR-Routing via Path-Segmente `/cockpit/[owner]/[repo]/[pr_number]` (nicht Query-Params)
- Next.js `output: 'export'` → Assets in `drift_cockpit/static/` → Hatchling embeds → `importlib.resources` zur Laufzeit
- In-Progress-Scan via 3s-Polling auf `GET /prs/{pr_id}/scan-status` (kein SSE)
- `drift cockpit serve` = `@cockpit_cmd.command('serve')` mit FastAPI + StaticFiles + `--port` + `--api-url`

## Phase 1 Design Outputs

- [data-model.md](data-model.md): Alle Frontend-Entitäten, Beziehungen, Client-State-Shape und Zustandsübergänge
- [contracts/frontend-api-contract.md](contracts/frontend-api-contract.md): Vollständiger API-Contract Frontend ↔ Backend inkl. Fehlerbehandlung
- [quickstart.md](quickstart.md): End-to-end lokaler Flow (Backend starten → Frontend dev → Build → `drift cockpit serve`)

## Post-Design Constitution Re-check

- [x] Library-First: `_serve.py` ist reiner Adapter; Entscheidungslogik bleibt in `decision_cockpit`-Kern
- [x] Test-First: Vitest-Tests für alle 5 Komponenten + Playwright-E2E + pytest für `serve`-Command vorgeplant
- [x] Vertical Slices: `packages/cockpit-ui/` eigenständig; Python-Erweiterung in bestehendem Slice ohne Sibling-Import
