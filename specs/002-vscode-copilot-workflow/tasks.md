# Tasks: VS Code Copilot Chat Workflow Integration

**Feature**: `002-vscode-copilot-workflow`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Generated**: 2026-04-27  
**Total tasks**: 19 | **User stories**: 3 (P1, P2, P3)

---

## Phase 1: Setup

*Project initialization — no blocking dependencies. Both tasks are parallelizable.*

- [X] T001 [P] Add `.vscode/drift-session.json` to `.gitignore` (specific entry, not blanket `.vscode/`)
- [X] T002 [P] Add `"chat.promptFilesLocations": [".github/prompts/"]` to `.vscode/settings.json`

---

## Phase 2: Foundational — `src/drift/copilot_handoff/` Library

*Must complete before all user story phases. Tests written first (Constitution §II).*

**Story goal**: Standalone, fully-tested library module that builds `SessionData`, `HandoffBlock`, and renders/serializes both — with zero CLI dependencies.

**Independent test criteria**: `pytest tests/test_copilot_handoff.py` passes all 9 tests in isolation from CLI code.

- [X] T003 Write failing unit tests in `tests/test_copilot_handoff.py` (10 stubs: `test_build_session_data_top5_by_severity`, `test_build_session_data_fewer_than_5_findings`, `test_build_session_data_empty_findings`, `test_write_session_file_creates_file`, `test_write_session_file_skips_when_no_vscode_dir`, `test_write_session_file_is_valid_json`, `test_session_data_roundtrip_write_and_read`, `test_build_handoff_block_has_3_prompts`, `test_handoff_to_dict_schema`, `test_render_handoff_rich_no_exception`) — all must fail RED before T005
- [X] T004 [P] Create `src/drift/copilot_handoff/` package skeleton: empty `__init__.py`, `_models.py`, `_session.py`, `_handoff.py`
- [X] T005 Implement frozen Pydantic models `TopFinding`, `SessionData`, `HandoffBlock` in `src/drift/copilot_handoff/_models.py` per `data-model.md`
- [X] T006 [P] Implement `build_session_data(analysis: RepoAnalysis) -> SessionData` and `write_session_file(repo: Path, data: SessionData) -> Path | None` in `src/drift/copilot_handoff/_session.py`
- [X] T007 [P] Implement `build_handoff_block(session: SessionData) -> HandoffBlock`, `render_handoff_rich(block: HandoffBlock, console: Console) -> None`, and `handoff_to_dict(block: HandoffBlock) -> dict` in `src/drift/copilot_handoff/_handoff.py`
- [X] T008 Export public API in `src/drift/copilot_handoff/__init__.py`: `build_session_data`, `write_session_file`, `build_handoff_block`, `render_handoff_rich`, `handoff_to_dict`
- [X] T009 Run `pytest tests/test_copilot_handoff.py -v` — confirm all 9 tests GREEN

---

## Phase 3 — User Story 1: Guided Fix Plan After Analysis (P1)

**Story goal**: After `drift analyze`, the terminal shows a HandoffBlock panel with top 5 findings and `/drift-fix-plan` slash command; JSON output includes a `copilot_handoff` key; `.vscode/drift-session.json` is written.

**Independent test criteria**: Run `drift analyze --repo .` — terminal output contains a `Copilot Chat Handoff` panel; `cat .vscode/drift-session.json` is valid JSON matching `contracts/session-file-schema.md`; `drift analyze --format json` output contains `"copilot_handoff"` key.

- [X] T010 [P] [US1] Write failing test for `analysis_to_json()` `copilot_handoff` key inclusion: add `test_analysis_to_json_includes_copilot_handoff_when_passed` to `tests/test_copilot_handoff.py` *(this is the 11th test — 10 from T003 + this one)*
- [X] T011 [P] [US1] Create `.github/prompts/drift-fix-plan.prompt.md` per `contracts/prompt-file-structure.md`: YAML frontmatter (`name: drift-fix-plan`), session context block (read `.vscode/drift-session.json`, staleness check), workflow steps (drift_fix_plan MCP call), output section, next-step handoff to `/drift-auto-fix-loop`
- [X] T012 [US1] Add optional `copilot_handoff: dict | None = None` keyword param to `analysis_to_json()` in `src/drift/output/json_output.py`; append to `data` dict when not `None` (GREEN for T010)
- [X] T013 [US1] Add `copilot_handoff: dict | None = None` keyword-only param to `render_or_emit_output()` in `src/drift/commands/_shared.py`; pass through to `analysis_to_json()` when `output_format == "json"`
- [X] T014 [US1] Integrate into `analyze()` in `src/drift/commands/analyze.py`: after `_render_analysis_details()` and before `_run_interactive_review()`, call `build_session_data()`, `write_session_file()`, `build_handoff_block()`, then `render_handoff_rich()` when `output_format == "rich" and not quiet`, and pass `handoff_to_dict()` result via `copilot_handoff` param when `output_format == "json"` and `not output_file`

---

## Phase 4 — User Story 2: Export Findings as a Report (P2)

**Story goal**: Developer invokes `/drift-export-report` in Copilot Chat and receives a self-contained markdown report from session context.

**Independent test criteria**: Open `/drift-export-report` in Copilot Chat with a populated `.vscode/drift-session.json` — prompt reads session file, generates a markdown document with findings, composite score, and per-signal breakdown, readable without drift knowledge.

- [X] T015 [US2] Create `.github/prompts/drift-export-report.prompt.md` per `contracts/prompt-file-structure.md`: YAML frontmatter (`name: drift-export-report`), session context block with staleness check, workflow steps (read session file, generate structured markdown with grade + top findings + counts + recommended actions; if session context includes a completed fix plan, include it as a separate "Fix Plan" section), output section (self-contained markdown, no tool access required to read), next-step handoff to "share externally or file a ticket"

---

## Phase 5 — User Story 3: Start Auto-Fix Loop (P3)

**Story goal**: Developer invokes `/drift-auto-fix-loop` and enters a guided one-finding-at-a-time remediation loop with explicit confirmation gates.

**Independent test criteria**: Open `/drift-auto-fix-loop` with a prepared findings context — prompt presents exactly one finding per iteration, asks confirm/skip before proceeding, maintains a running summary, and offers `/drift-export-report` when loop completes.

- [X] T016 [US3] Create `.github/prompts/drift-auto-fix-loop.prompt.md` per `contracts/prompt-file-structure.md`: YAML frontmatter (`name: drift-auto-fix-loop`), session context block with staleness check, workflow steps (read session file, iterate findings one-at-a-time using `drift_fix_plan` MCP, require confirm/skip per finding, track applied/skipped in running summary, handle stale file-path references with skip+warn), stop condition (all findings processed or skipped), output section (loop summary), next-step handoff to `/drift-export-report`

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 Run `ruff check src/drift/copilot_handoff/ src/drift/output/json_output.py src/drift/commands/_shared.py src/drift/commands/analyze.py` — zero violations
- [X] T018 Run `mypy src/drift/copilot_handoff/ src/drift/output/json_output.py src/drift/commands/_shared.py src/drift/commands/analyze.py` — zero type errors
- [X] T019 Run full quick test suite `pytest tests/ -m "not slow" --ignore=tests/test_smoke_real_repos.py -q` — all GREEN

---

## Dependencies

```
T001 ──────────────────────────────────────────────────────► (independent)
T002 ──────────────────────────────────────────────────────► (independent)

T003 ──► T005
T004 ──► T005
         T005 ──► T006
                  T006 ──► T008
         T005 ──► T007
                  T007 ──► T008
                            T008 ──► T009

T009 ──► T010 ──► T012 ──► T013 ──► T014
T009 ──► T011 (independent of T010/T012/T013)

T011 ──► T015 (prompt chain: fix-plan → export-report reference)
T015 ──► T016 (prompt chain: export-report → auto-fix-loop reference)

T014, T016 ──► T017 ──► T019
T014, T016 ──► T018 ──► T019
```

---

## Parallel Execution Per Phase

**Phase 2 parallelism**:
- Write T003 (tests) while creating T004 (package skeleton) — both target different files
- After T005 passes: run T006 and T007 simultaneously — `_session.py` and `_handoff.py` share `_models.py` imports but don't depend on each other

**Phase 3 parallelism**:
- T010 (test stub for json_output extension) and T011 (drift-fix-plan.prompt.md) are fully independent — start both simultaneously
- T012 → T013 → T014 are sequential (each extends the previous layer)

**Phase 4–5 parallelism**:
- T015 and T016 can be drafted in parallel if T011 exists (prompt chain references are stable)

---

## Implementation Strategy

**MVP scope (US1 only — Tasks T001–T014)**:
- After T001–T014, `drift analyze` emits a HandoffBlock and writes a session file
- `/drift-fix-plan` is invocable from Copilot Chat
- This is the minimum viable handoff and can be validated end-to-end before building US2/US3

**Incremental delivery**:
1. T001–T009: Library complete, fully tested in isolation
2. T010–T014: CLI integration complete (US1 done — SC-001, SC-002, SC-003 satisfied)
3. T015: Report export added (US2 done — SC-006 satisfied)
4. T016: Auto-fix loop added (US3 done — SC-005 fully satisfied)
5. T017–T019: Polish and gate check

---

## Format Validation

All tasks follow the required checklist format:  
`- [ ] T### [P]? [US#]? Description with file path`

- ✅ All 19 tasks have checkbox + sequential ID
- ✅ Parallelizable tasks marked `[P]`: T001, T002, T004, T006, T007, T010, T011
- ✅ User story tasks labeled `[US1]`–`[US3]`: T010–T016
- ✅ Setup/Foundational/Polish tasks: no story label
- ✅ Every task references a concrete file path
