# Tasks: Drift Cockpit Frontend

**Input**: Design documents from `/specs/007-cockpit-frontend/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/frontend-api-contract.md ✅, quickstart.md ✅
**Branch**: `011-cockpit-frontend`

---

## Phase 1: Setup

**Purpose**: New Next.js package scaffold and Python serve-command skeleton

- [X] T001 Scaffold `packages/cockpit-ui/` with Next.js 14 (`output: 'export'`), TypeScript, Tailwind CSS, Vitest, Playwright per `packages/cockpit-ui/package.json` + `next.config.js`
- [X] T002 [P] Create `packages/cockpit-ui/src/types/cockpit.ts` with all TypeScript types from `specs/007-cockpit-frontend/data-model.md` (PrRef, DecisionPanel, RiskDriver, MinimalSafePlan, GuardrailCondition, AccountabilityCluster, ClusterFile, LedgerEntry, OutcomeRecord, CockpitStore)
- [X] T003 [P] Create `packages/cockpit-ui/src/api/client.ts` — typed REST client reading `COCKPIT_API_URL` from `next.config.js` env; implements all endpoints from `specs/007-cockpit-frontend/contracts/frontend-api-contract.md`
- [X] T004 [P] Create `packages/drift-cockpit/src/drift_cockpit/_serve.py` — FastAPI app with `StaticFiles` mount + `/api/cockpit/*` proxy stub; `importlib.resources` locates `static/` at runtime
- [X] T005 Extend `packages/drift-cockpit/src/drift_cockpit/_cmd.py` — add `serve` subcommand (`--port`, `--api-url`) that starts the FastAPI app from `_serve.py`
- [X] T006 [P] Create `packages/drift-cockpit/src/drift_cockpit/static/.gitkeep` and update `packages/drift-cockpit/pyproject.toml` with hatchling include glob `src/drift_cockpit/static/**`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: App shell, routing, shared layout, API client wiring and Python serve test skeleton — must be complete before any user story component work begins

**⚠️ CRITICAL**: All user story phases depend on this phase being complete

- [X] T007 Create Next.js app route `packages/cockpit-ui/src/app/cockpit/[owner]/[repo]/[pr_number]/page.tsx` — server component that passes segments to client shell
- [X] T008 [P] Create `packages/cockpit-ui/src/app/layout.tsx` — root layout with Tailwind globals, font, and error boundary
- [X] T009 [P] Create `packages/cockpit-ui/src/hooks/useScanStatus.ts` — 3-second polling hook; stops when `status = "complete"`; exposes `{ status, progress }`
- [X] T010 [P] Create `packages/cockpit-ui/src/hooks/useDecisionPanel.ts` — fetches panel; triggers polling via `useScanStatus` when scan running; exposes `{ panel, loading, error }`
- [X] T011 [P] Create `packages/cockpit-ui/src/components/ErrorBanner/index.tsx` — reusable error/conflict banner; accepts `message`, `type: "error"|"conflict"`
- [X] T012 [P] Create `packages/cockpit-ui/src/components/LoadingIndicator/index.tsx` — progress bar + percentage; shown when `scan_status = "running"`
- [X] T013 [P] Create `packages/cockpit-ui/tests/e2e/cockpit.spec.ts` — Playwright E2E skeleton with mock server fixtures for all 5 user stories (stubs only, will fail until US implementations complete)
- [X] T014 [P] Create `tests/decision_cockpit/test_cockpit_serve_cmd.py` — pytest skeleton testing `drift cockpit serve --port 9123` starts, responds 200 on `/`, and `--help` includes `api-url` option

**Checkpoint**: App shell renders at `/cockpit/owner/repo/123`, polling hook wires to API, error+loading components exist, all test skeletons RED

---

## Phase 3: User Story 1 — PR-Entscheidungsstatus auf einen Blick (Priority: P1) 🎯 MVP

**Goal**: Maintainerin sieht Status-Badge, Konfidenzwert und Top-Risikotreiber im ersten Viewport — sofort, ohne weitere Werkzeuge.

**Independent Test**: Cockpit-URL für PR öffnen → Decision Panel zeigt Status, Konfidenz und ≥1 Risikotreiber in <2 s; bei fehlender Evidenz: No-Go mit Hinweis.

- [X] T015 [P] [US1] Create `packages/cockpit-ui/src/components/DecisionPanel/StatusBadge.tsx` — renders Go / Go with Guardrails / No-Go with distinct colour per status; `evidence_sufficient=false` forces No-Go variant with explanatory text
- [X] T016 [P] [US1] Create `packages/cockpit-ui/src/components/DecisionPanel/ConfidenceBar.tsx` — numeric confidence value (0–1) as labelled progress bar
- [X] T017 [P] [US1] Create `packages/cockpit-ui/src/components/DecisionPanel/RiskDriverList.tsx` — sorted-by-impact list; first item visually highlighted; renders `impact`, `severity` badge, optional `cluster_id` link
- [X] T018 [US1] Create `packages/cockpit-ui/src/components/DecisionPanel/index.tsx` — composes StatusBadge + ConfidenceBar + RiskDriverList; passes `DecisionPanel` type from `cockpit.ts`; shows `LoadingIndicator` while `scan_status = "running"`
- [X] T019 [US1] Wire `DecisionPanel` into `packages/cockpit-ui/src/app/cockpit/[owner]/[repo]/[pr_number]/page.tsx` via `useDecisionPanel` hook
- [X] T020 [P] [US1] Write Vitest component tests for `StatusBadge`, `ConfidenceBar`, `RiskDriverList` in `packages/cockpit-ui/tests/components/DecisionPanel.test.tsx` — cover Go/Guardrails/No-Go variants, no-evidence forced state, sort order

**Checkpoint**: US1 independently testable — `npm test` passes DecisionPanel tests; Playwright US1 E2E scenario green

---

## Phase 4: User Story 2 — Minimal-Safe-Plan einsehen und Guardrails verstehen (Priority: P1)

**Goal**: Maintainerin sieht Plan-Karten mit Risiko-Delta, Score-Delta und abhakbarer Guardrail-Checkliste; alle Bedingungen erfüllt → visuelle Bestätigung.

**Independent Test**: PR mit No-Go laden → mindestens eine Plan-Karte mit Deltas + Checkliste; Guardrail abhaken → optimistischer Toggle ohne Reload; alle abhaken → Completion-Badge erscheint.

- [X] T021 [P] [US2] Create `packages/cockpit-ui/src/components/MinimalSafePlanCard/GuardrailChecklist.tsx` — ordered checklist with individual `fulfilled` toggle; PATCH `guardrails/{condition_id}` on toggle (debounced 400 ms); all fulfilled → completion badge
- [X] T022 [P] [US2] Create `packages/cockpit-ui/src/components/MinimalSafePlanCard/DeltaBadge.tsx` — renders `risk_delta` and `score_delta` as signed numeric badges with colour (negative = improvement = green)
- [X] T023 [US2] Create `packages/cockpit-ui/src/components/MinimalSafePlanCard/index.tsx` — composes title + DeltaBadge + GuardrailChecklist; collapses by default, expands on click
- [X] T024 [US2] Create `packages/cockpit-ui/src/components/MinimalSafePlanList/index.tsx` — fetches `GET /prs/{pr_id}/safe-plan`; renders ordered list of `MinimalSafePlanCard`; empty state when no plans available
- [X] T025 [US2] Wire `MinimalSafePlanList` into cockpit page as Safe-Plan tab (via T042 tab navigation); visible when tab active
- [X] T026 [P] [US2] Write Vitest tests for `GuardrailChecklist`, `DeltaBadge`, `MinimalSafePlanCard` in `packages/cockpit-ui/tests/components/MinimalSafePlan.test.tsx` — cover toggle behaviour, debounce, completion badge, empty-plan state

**Checkpoint**: US2 independently testable — `npm test` passes MinimalSafePlan tests; Playwright US2 E2E scenario green

---

## Phase 5: User Story 3 — Accountability Graph für Risikocluster (Priority: P2)

**Goal**: Maintainerin sieht PR-Änderungen in Risikoclustern mit prozentualem Anteil; dominanter Cluster visuell hervorgehoben; Klick auf Cluster klappt Dateien auf.

**Independent Test**: Graph-Tab aufrufen → Cluster-Knoten mit Risikoanteilen sichtbar; dominanter Cluster hervorgehoben; Klick → Dateiliste expandiert.

- [X] T027 [P] [US3] Create `packages/cockpit-ui/src/components/AccountabilityGraph/ClusterNode.tsx` — renders cluster label, `risk_share` as percentage bar; `dominant=true` → highlighted border + icon
- [X] T028 [P] [US3] Create `packages/cockpit-ui/src/components/AccountabilityGraph/ClusterFileList.tsx` — expandable list of `ClusterFile[]` with individual `contribution` percentage; toggled by click on parent
- [X] T029 [US3] Create `packages/cockpit-ui/src/components/AccountabilityGraph/index.tsx` — fetches `GET /prs/{pr_id}/clusters`; renders sorted `ClusterNode` list (descending `risk_share`); wires expand/collapse per cluster
- [X] T030 [US3] Add `?tab=graph` routing to cockpit page — renders `AccountabilityGraph` when tab active; default tab is `panel`
- [X] T031 [P] [US3] Write Vitest tests for `ClusterNode`, `ClusterFileList`, `AccountabilityGraph` in `packages/cockpit-ui/tests/components/AccountabilityGraph.test.tsx` — cover dominant highlight, sort order, expand/collapse, ≤50 clusters render performance

**Checkpoint**: US3 independently testable — `npm test` passes AccountabilityGraph tests; Playwright US3 E2E scenario green

---

## Phase 6: User Story 4 — Entscheidung treffen und Ledger eintragen (Priority: P1)

**Goal**: Maintainerin erfasst Go/No-Go/Guardrails direkt im Formular; Abweichung von App-Empfehlung erfordert Pflicht-Begründung; Versionskonflikt wird angezeigt.

**Independent Test**: Formular absenden → Ledger-Eintrag mit Zeitstempel erscheint; Abweichung ohne Begründung → Formular blockiert; Versionskonflikt → Conflict-Banner.

- [X] T032 [P] [US4] Create `packages/cockpit-ui/src/components/DecisionForm/DecisionSelector.tsx` — radio group for Go / Go with Guardrails / No-Go; highlights app recommendation
- [X] T033 [P] [US4] Create `packages/cockpit-ui/src/components/DecisionForm/JustificationField.tsx` — textarea; required (non-empty) when human choice differs from `app_recommendation`; shows validation message if empty on submit
- [X] T034 [US4] Create `packages/cockpit-ui/src/components/DecisionForm/index.tsx` — composes DecisionSelector + JustificationField + submit button; POSTs `DecisionWriteRequest` with current `version`; on 409 → renders `ErrorBanner` with `type="conflict"` and blocks further edits; on success → triggers ledger refresh
- [X] T035 [US4] Wire `DecisionForm` into cockpit page below `DecisionPanel`; hidden once `human_decision` already recorded
- [X] T036 [P] [US4] Write Vitest tests for `DecisionForm` in `packages/cockpit-ui/tests/components/DecisionForm.test.tsx` — cover justification required when overriding, submit blocked without justification, 409 conflict banner, success → form hidden

**Checkpoint**: US4 independently testable — `npm test` passes DecisionForm tests; Playwright US4 E2E scenario green

---

## Phase 7: User Story 5 — Decision Ledger und Outcomes nachverfolgen (Priority: P2)

**Goal**: Maintainerin sieht chronologische Timeline aus Empfehlung, Entscheidung, Evidenzreferenzen und 7/30-Tage-Outcomes; fehlende Outcomes explizit als ausstehend markiert.

**Independent Test**: Ledger-Tab aufrufen → Timeline mit allen Feldern; `outcome_7d.status = "pending"` → Label "ausstehend", kein leeres Feld; 30d-Outcome eingetragen → im selben Eintrag sichtbar.

- [X] T037 [P] [US5] Create `packages/cockpit-ui/src/components/LedgerTimeline/TimelineEntry.tsx` — renders app recommendation, human decision (or "pending"), evidence refs as links, outcome slots
- [X] T038 [P] [US5] Create `packages/cockpit-ui/src/components/LedgerTimeline/OutcomeSlot.tsx` — renders `OutcomeRecord`; `status = "pending"` → explicit "ausstehend" badge; `status = "available"` → outcome value + `recorded_at`
- [X] T039 [US5] Create `packages/cockpit-ui/src/components/LedgerTimeline/index.tsx` — fetches `GET /prs/{pr_id}/ledger`; renders `TimelineEntry` with 7d and 30d `OutcomeSlot`; refreshes after DecisionForm submit
- [X] T040 [US5] Add `?tab=ledger` routing to cockpit page — renders `LedgerTimeline` when tab active
- [X] T041 [P] [US5] Write Vitest tests for `LedgerTimeline`, `TimelineEntry`, `OutcomeSlot` in `packages/cockpit-ui/tests/components/LedgerTimeline.test.tsx` — cover pending outcome label, available outcome display, evidence refs, timeline order

**Checkpoint**: US5 independently testable — `npm test` passes LedgerTimeline tests; Playwright US5 E2E scenario green

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Build pipeline, Python serve integration, tab navigation, error states, performance validation

- [X] T042 Add tab navigation bar to cockpit page — Panel (default) / Safe Plan / Graph / Ledger; active tab from `?tab=` query param; keyboard-accessible
- [X] T043 Implement global error boundary in `packages/cockpit-ui/src/app/cockpit/[owner]/[repo]/[pr_number]/page.tsx` — renders `ErrorBanner` on fetch errors, timeouts, 5xx; never blank page (FR-012)
- [X] T044 [P] Implement `parsePrUrl(url: string): PrRef | null` in `packages/cockpit-ui/src/api/client.ts` — regex extracts owner/repo/pr_number from GitHub PR URL; invalid input returns null with user-friendly error (FR-016)
- [X] T045 [P] Add landing page `packages/cockpit-ui/src/app/page.tsx` — GitHub PR-URL input field; on submit navigates to `/cockpit/[owner]/[repo]/[pr_number]` using `parsePrUrl`; invalid URL → inline error
- [X] T046 Build Next.js static export and copy `out/` to `packages/drift-cockpit/src/drift_cockpit/static/` — document in `Makefile` as `make cockpit-build`
- [X] T047 [P] Implement `packages/drift-cockpit/src/drift_cockpit/_serve.py` fully — FastAPI mounts `StaticFiles` from `importlib.resources`; proxies `/api/cockpit/*` to `COCKPIT_API_URL`; handles startup error when static dir empty with clear message
- [X] T048 Complete `tests/decision_cockpit/test_cockpit_serve_cmd.py` — assert serve starts on `--port`, responds 200 on `/`, validates `--api-url` is passed to proxy, empty static dir produces informative error
- [X] T049 [P] Write Vitest tests for `parsePrUrl` and landing page in `packages/cockpit-ui/tests/components/LandingPage.test.tsx` — valid URLs, invalid URLs, navigation trigger
- [X] T050 [P] Write Playwright viewport tests for ≥1024px Desktop responsiveness in `packages/cockpit-ui/tests/e2e/viewport.spec.ts` — confirm all panels/tabs layout correctly at 1024px, 1280px, 1920px viewports (FR-014 coverage)
- [X] T051 Run full Playwright E2E suite against mock backend; confirm all 5 US scenarios green; confirm SC-001 (<2 s panel load) with Playwright `page.metrics()`

---

## Dependencies

```
Phase 1 (Setup)
  └── Phase 2 (Foundational: app shell, hooks, skeletons)
        ├── Phase 3 (US1 Decision Panel) ← MVP — deliver first
        ├── Phase 4 (US2 Safe Plans)     ← depends on Phase 3 tab shell
        ├── Phase 5 (US3 Graph)          ← parallel with US2 after Phase 2
        ├── Phase 6 (US4 Decision Form)  ← depends on Phase 3 (panel data)
        └── Phase 7 (US5 Ledger)         ← depends on Phase 6 (decision write)
              └── Phase 8 (Polish)       ← all US complete
```

## Parallel Execution per Story

Each story phase is independently executable after Phase 2 completes:

| Phase | Parallelisable tasks |
|-------|---------------------|
| 3 | T015, T016, T017, T020 in parallel |
| 4 | T021, T022, T026 in parallel; T023→T024 sequential |
| 5 | T027, T028, T031 in parallel; T029→T030 sequential |
| 6 | T032, T033, T036 in parallel; T034→T035 sequential |
| 7 | T037, T038, T041 in parallel; T039→T040 sequential |

## MVP Scope

Implement **Phase 1 + Phase 2 + Phase 3** first. This delivers US1 (Decision Panel), which is the single highest-value increment: a working cockpit URL showing status, confidence and risk drivers for any analysed PR.

| Phase | Tasks | US |
|-------|-------|----|
| Phase 1 | T001–T006 | — |
| Phase 2 | T007–T014 | — |
| Phase 3 | T015–T020 | US1 ✅ |
