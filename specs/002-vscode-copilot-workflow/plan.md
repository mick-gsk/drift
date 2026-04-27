# Implementation Plan: VS Code Copilot Chat Workflow Integration

**Branch**: `002-vscode-copilot-workflow` | **Date**: 2026-04-27 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `specs/002-vscode-copilot-workflow/spec.md`

## Summary

Extend `drift analyze` to write a local `.vscode/drift-session.json` after every analysis run and append a HandoffBlock (Rich panel + JSON key) that surfaces the top 5 findings and three clickable VS Code Copilot Chat slash-command prompts (`/drift-fix-plan`, `/drift-export-report`, `/drift-auto-fix-loop`). Three `.prompt.md` files under `.github/prompts/` implement the guided analysis-to-remediation workflow. A single `chat.promptFilesLocations` entry in `.vscode/settings.json` wires discovery — zero additional installs required.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic (`frozen=True`), Rich (Panel), Click (CLI), pytest  
**Storage**: `.vscode/drift-session.json` — local JSON file, always gitignored  
**Testing**: pytest; TDD cycle enforced (tests written first, per Constitution §II)  
**Target Platform**: Desktop VS Code 1.90+ with GitHub Copilot Chat extension  
**Project Type**: Feature addition to existing CLI library (`src/drift/`)  
**Performance Goals**: HandoffBlock render ≤ 10ms overhead on top of existing analysis budget  
**Constraints**: Zero additional runtime dependencies; no network calls; no VS Code extension install  
**Scale/Scope**: 1 new library sub-package, 3 new prompt files, 3 minimal touchpoints in existing code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: All HandoffBlock and session logic lives in `src/drift/copilot_handoff/`. `analyze.py` is a thin caller with no core logic. `json_output.py` accepts an optional `copilot_handoff` dict param — all computation is in the library.
- [x] **II. Test-First**: `tests/test_copilot_handoff.py` with 9 failing tests written before any implementation. Precision/recall fixtures unchanged (no signal modification).
- [x] **III. Functional Programming**: `build_session_data()` and `build_handoff_block()` are pure functions. `write_session_file()` is the only I/O function, isolated at the file boundary. All models are frozen Pydantic.
- [x] **IV. CLI Interface & Observability**: HandoffBlock appended to existing Rich and JSON output paths. No new Click subcommand needed (existing `analyze` extended). SARIF/CSV/markdown formats are unaffected.
  > **§IV exemption** (YAGNI — §V): `src/drift/copilot_handoff/` is an internal integration support library invoked exclusively by `analyze.py`. Constitution §IV applies to user-facing analysis libraries that surface new analysis commands. No standalone Click subcommand is justified for a pass-through session-writer.
- [x] **V. Simplicity & YAGNI**: 1 new library sub-package (4 files), 3 static prompt files, 3 touchpoints in existing code. No abstraction layers, no plugin system, no caching. Every function justified by a spec requirement.

**Post-Design Re-check**: All 5 principles pass. The optional `copilot_handoff` param on `analysis_to_json` is the minimal change needed — no alternative is simpler without violating Library-First.

## Project Structure

### Documentation (this feature)

```text
specs/002-vscode-copilot-workflow/
├── plan.md                             # This file
├── spec.md                             # Feature specification
├── research.md                         # Phase 0 research output
├── data-model.md                       # Phase 1 data model
├── quickstart.md                       # Phase 1 quickstart guide
├── contracts/
│   ├── session-file-schema.md          # .vscode/drift-session.json contract
│   ├── prompt-file-structure.md        # .prompt.md file structure contract
│   └── json-output-extension.md        # copilot_handoff JSON key contract
└── tasks.md                            # Phase 2 (speckit.tasks — NOT created here)
```

### Source Code Changes

```text
# New library module
src/drift/copilot_handoff/
├── __init__.py          # Public exports
├── _models.py           # TopFinding, SessionData, HandoffBlock (all frozen Pydantic)
├── _session.py          # build_session_data(), write_session_file()
└── _handoff.py          # build_handoff_block(), render_handoff_rich(), handoff_to_dict()

# New tests
tests/
└── test_copilot_handoff.py   # 9 unit tests — library only, no CLI

# Modified files (minimal changes)
src/drift/commands/analyze.py            # +write_session_file() + render_handoff_rich() call after _render_analysis_details()
src/drift/output/json_output.py          # +copilot_handoff: dict | None = None param in analysis_to_json()
src/drift/commands/_shared.py            # +copilot_handoff kwarg passed through to analysis_to_json()

# New static prompt files
.github/prompts/
├── drift-fix-plan.prompt.md
├── drift-export-report.prompt.md
└── drift-auto-fix-loop.prompt.md

# Config changes
.vscode/settings.json                    # +chat.promptFilesLocations
.gitignore                               # +.vscode/drift-session.json
```

**Structure Decision**: Single project layout — feature extends existing `src/drift/` library with one new sub-package. No new projects, services, or layers needed.

## Complexity Tracking

No Constitution violations. All abstractions are directly justified by spec requirements:

| Module | Justified By |
|--------|-------------|
| `_models.py` separate file | Constitution §III: frozen models; avoids circular imports with session/handoff logic |
| `_session.py` / `_handoff.py` split | Single Responsibility: session persistence vs. output rendering are distinct concerns |
| Optional param in `analysis_to_json` | Avoids code duplication while preserving backward compat (contracts/json-output-extension.md) |
