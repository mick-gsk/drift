# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify each principle from `.specify/memory/constitution.md` (v1.1.0):

- [ ] **I. Library-First**: Is the new functionality implemented as a standalone library
  under `src/drift/`? Does no CLI command or MCP handler contain core logic?
- [ ] **II. Test-First**: Are failing tests written and approved BEFORE implementation
  begins? Are precision/recall fixtures updated for any signal changes?
- [ ] **III. Functional Programming**: Do new modules use pure functions and frozen
  Pydantic models? Are side effects isolated at system boundaries (CLI, Git, I/O)?
- [ ] **IV. CLI Interface & Observability**: Does the library expose a Click subcommand?
  Are both JSON and Rich output formats supported?
- [ ] **V. Simplicity & YAGNI**: Is every abstraction justified by a concrete, failing test
  or benchmark delta? Is there a simpler alternative that was considered and rejected?
- [ ] **VI. Vertical Slices**: Is the feature organized as a self-contained slice
  under `src/drift/<feature_name>/`? Does it own its own models, logic, and CLI
  subcommand? Are cross-slice dependencies expressed only through public module
  interfaces — no imports of sibling-slice internals?

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
<!--
  ACTION REQUIRED: Replace the placeholder tree below with the concrete layout
  for this feature. Delete unused options and expand the chosen structure with
  real paths (e.g., apps/admin, packages/something). The delivered plan must
  not include Option labels.
-->

```text
# [REMOVE IF UNUSED] Option 1: Vertical Slice (DEFAULT for Drift features)
# Each slice owns its models, logic, CLI subcommand, and tests.
src/drift/<feature_name>/
├── __init__.py          # Public API surface — no internals exported
├── _models.py           # Frozen Pydantic models (private to slice)
├── _detector.py         # Core detection / processing logic (pure functions)
├── _output.py           # Output formatting (Rich + JSON)
└── _cmd.py              # Click subcommand registration

tests/<feature_name>/
├── test_<feature>_unit.py       # Pure-function unit tests
├── test_<feature>_contract.py   # Public API contract tests
└── test_<feature>_integration.py

# [REMOVE IF UNUSED] Option 2: New signal (Signal slice)
src/drift/signals/<signal_name>.py   # Single-file slice when logic is compact
tests/test_signals_<signal_name>.py

# [REMOVE IF UNUSED] Option 3: Multi-layer feature (only when explicitly required)
# Use ONLY if the feature spans ingestion + signals + output and cannot be
# decomposed into independent slices. Must be justified in Complexity Tracking.
src/drift/<feature_name>/
├── ingestion/
├── signals/
└── output/
tests/<feature_name>/
```

**Structure Decision**: [Document the selected structure and reference the real
directories captured above]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
