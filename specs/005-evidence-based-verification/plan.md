# Implementation Plan: 005 Evidence-Based Drift Verification

**Branch**: `feat/adr100-phase7a-cleanup` | **Date**: 2026-05-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/005-evidence-based-verification/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Neues `drift verify`-Command, das ein Change-Set (Unified Diff) deterministisch gegen Architekturregeln (AVS/PFS/EDS), Spec-Akzeptanzkriterien und optionalen Independent Review prüft. Ergebnis: maschinenlesbares Evidence Package (JSON `evidence-package-v1`) mit Drift Score, Spec Confidence Score und `ActionRecommendation` (automerge / needs_fix / needs_review / escalate_to_human). Rule-Promotion-Mechanismus erkennt wiederkehrende Violations und schlägt dauerhafte Regeln vor.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic (frozen models), Click (CLI), Rich (terminal output), pytest / mypy / ruff  
**Storage**: `.drift/pattern_history.jsonl` im Repo-Root (JSONL append, kein DB)  
**Testing**: pytest + mypy typecheck; ground-truth fixtures in `tests/verify/`  
**Target Platform**: Linux / macOS / Windows (cross-platform)  
**Project Type**: library/cli (Vertical Slice in `src/drift/verify/`)  
**Performance Goals**: Evidence Package in ≤3 min für typischen Feature-Diff (SC-001)  
**Constraints**: Kein LLM-Aufruf in deterministischer Schicht; Reviewer Agent via `ReviewerAgentProtocol` isoliert; `--no-reviewer` muss immer schnell arbeiten  
**Scale/Scope**: Einzelner Diff-Check pro Aufruf; Batch-Modus nicht in v1

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify each principle from `.specify/memory/constitution.md` (v1.1.0):

- [x] **I. Library-First**: Gesamte Logik in `src/drift/verify/`; `_cmd.py` (Click) enthält nur Argument-Parsing + Aufruf der öffentlichen API `verify(change_set)`.
- [x] **II. Test-First**: Failing tests für `EvidencePackage`, `ActionRecommendation` und alle Verdicts werden vor Implementierung geschrieben (TDD Red-Green-Refactor).
- [x] **III. Functional Programming**: Alle Modelle `frozen=True`; `_checker.py` und `_promoter.py` als pure functions; I/O nur in `_cmd.py` und JSONL-Append in `_promoter.py`.
- [x] **IV. CLI Interface & Observability**: `drift verify` mit `--format json|rich`; JSON = Evidence Package Schema v1; Rich = farbige Zusammenfassung.
- [x] **V. Simplicity & YAGNI**: Reviewer Agent ist durch SC-006 (Benchmark-Anforderung Independent Review) gerechtfertigt — siehe Complexity Tracking. Kein Batch-Modus, kein Plugin-System in v1.
- [x] **VI. Vertical Slices**: `src/drift/verify/` enthält eigene Modelle, Logik, Output und CLI-Command. Imports nur über `drift.analyze` public API, nicht interne Signals-Implementierungen.

## Project Structure

### Documentation (this feature)

```text
specs/005-evidence-based-verification/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
src/drift/verify/
├── __init__.py          # Public API: verify(change_set, ...) -> EvidencePackage
├── _models.py           # Alle frozen Pydantic models aus data-model.md
├── _checker.py          # Deterministischer Layer (wraps drift analyze Python API)
├── _reviewer.py         # ReviewerAgentProtocol + MockReviewerAgent + DriftMcpReviewerAgent
├── _promoter.py         # Rule-Promotion + .drift/pattern_history.jsonl
├── _output.py           # JSON-Serialisierung (evidence-package-v1) + Rich-Output
└── _cmd.py              # Click-Subcommand: drift verify

tests/verify/
├── test_verify_unit.py           # Pure-function tests für _checker, _promoter, _models
├── test_verify_contract.py       # Public-API-Vertrag (EvidencePackage Invarianten)
└── test_verify_integration.py    # End-to-End via CLI (subprocess oder invoke)

scripts/
└── generate_evidence_schema.py   # Analog zu generate_output_schema.py

specs/005-evidence-based-verification/
├── plan.md              # Dieses Dokument
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
└── contracts/           # Phase 1
    ├── cli-contract.md
    └── reviewer-agent-protocol.md
```

**Structure Decision**: Vertical Slice (Option 1). Eigenständige `src/drift/verify/` Slice mit eigenem Public API, Modellen, CLI-Command und Tests. Cross-Slice-Dependencies nur über `drift.api` (öffentliche Python-API von drift analyze).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `ReviewerAgentProtocol` Abstraction | SC-006 fordert Independent Review als separaten Verifikationsschritt im Benchmark | Direkte Inline-Prüfung könnte keine saubere Mock-Injektion für Tests bieten und würde LLM-Aufruf in deterministischen Layer einmischen |
| `IndependentReviewResult.confidence_delta` | Reviewer-Befund muss additiv auf Spec Confidence Score wirken, ohne ihn zu überschreiben (deterministische Basis bleibt kontrollierbar) | Score-Override wäre durch LLM-Antworten manipulierbar und widerspricht Constitution III (Functional/deterministic) |
| Netzwerkaufruf in `DriftMcpReviewerAgent` | Constitution V: „No network calls during analysis.“ gilt für deterministische Signale in `src/drift/signals/`. `drift verify` ist kein Signal-Modul, sondern ein optionaler Verifikations-Layer darüber. Der Netzwerkaufruf ist (a) hinter `ReviewerAgentProtocol` isoliert, (b) opt-in via `--reviewer` (Standard: an, aber deaktivierbar), (c) in Tests immer durch `MockReviewerAgent` ersetzt — kein Produktionscode in `src/drift/signals/` berührt. | Einen Reviewer ohne jede externe Kommunikation zu betreiben würde SC-006 unerfullbar machen und den Zweck des Independent Review zunichte machen. |
