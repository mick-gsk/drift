# Implementation Plan: findings-change-effort-coupling

**Branch**: `009-findings-change-effort-coupling` | **Date**: 2025-07-17 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/009-findings-change-effort-coupling/spec.md`

## Summary

Enrich the `description` and `fix` string fields of three mandatory signals (PFS, MDS, EDS) so that no finding is "pattern-only" — i.e., every finding names either a concrete layer/concern/boundary or a change implication. AVS findings are already exempt (they already name layers). Changes are purely string-content updates to three Python files plus a new smoke-check test file and a vocabulary addition to the finding-message-authoring SKILL.md. No structural model changes are needed.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic (frozen models), pytest, ruff, mypy — no new dependencies  
**Storage**: N/A — string content changes only; no persistence layer involved  
**Testing**: pytest; new test file `tests/test_finding_message_quality.py`; runs in `make check`  
**Target Platform**: All platforms (library code, no OS dependency)  
**Project Type**: Library — signal module string templates inside `src/drift/signals/`  
**Performance Goals**: No change — string template construction is O(1) per finding  
**Constraints**: ≤2 sentences per description (SKILL.md quality rule); no new fields on Finding  
**Scale/Scope**: 4 signal files, 4 Finding constructors (PFS×1, MDS×2, EDS×1); AVS exempt

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify each principle from `.specify/memory/constitution.md` (v1.0.0):

- [x] **I. Library-First**: Changes are within existing signal modules under `src/drift/signals/`. No CLI command or MCP handler contains new core logic. Signal files ARE the library — string template changes are contained library changes. ✅
- [x] **II. Test-First**: New smoke-check test file `tests/test_finding_message_quality.py` MUST be written with failing assertions BEFORE description/fix strings are updated. Precision/recall fixtures are not affected (no detection-logic changes). ✅
- [x] **III. Functional Programming**: Finding construction uses pure f-string/string-join expressions. No new mutable state or side effects introduced. Finding dataclass remains frozen. ✅
- [x] **IV. CLI Interface & Observability**: No new CLI command needed. Enriched description/fix strings propagate automatically to all output formats (Rich, JSON, SARIF) via existing renderers. ✅
- [x] **V. Simplicity & YAGNI**: No new abstraction. No new model field. No new module. String content update only. A structured `boundary_context` field was considered (more reusable) and rejected: spec clarification Q4 confirmed automatic propagation via strings is sufficient; adding a field requires touching all 24+ signals and migrating schema. ✅

## Project Structure

### Documentation (this feature)

```text
specs/009-findings-change-effort-coupling/
├── plan.md                          # This file
├── research.md                      # Phase 0 output — signal mapping + assessment
├── data-model.md                    # Phase 1 output — field change inventory
├── quickstart.md                    # Phase 1 output — how to run tests
├── contracts/
│   └── finding-message-quality.md  # Phase 1 output — keyword smoke-check contract
└── tasks.md                         # Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
src/drift/signals/
├── pattern_fragmentation.py   # PFS — edit description + fix (1 Finding constructor)
├── mutant_duplicates.py       # MDS — edit description + fix (2 Finding constructors)
├── explainability_deficit.py  # EDS — edit description + fix (1 Finding constructor)
└── architecture_violation.py  # AVS — no changes required (exempt)

tests/
└── test_finding_message_quality.py  # NEW — keyword smoke-check tests for PFS/MDS/EDS

.github/skills/drift-finding-message-authoring/
└── SKILL.md                         # Add "Boundary Vocabulary" section
```

**Structure Decision**: Single-project, library-first. Changes are localized to three existing signal files and one new test file. No new package, submodule, or CLI entrypoint needed.

## Complexity Tracking

> No Constitution violations — no entries required.
