# Tasks: findings-change-effort-coupling

**Input**: Design documents from `specs/009-findings-change-effort-coupling/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Signal–file mapping** (from research.md):
- PFS → `src/drift/signals/pattern_fragmentation.py` (1 Finding constructor, description line ~459, fix line ~462)
- MDS → `src/drift/signals/mutant_duplicates.py` (2 Finding constructors: exact-dup ~line 425, near-dup ~line 604)
- EDS → `src/drift/signals/explainability_deficit.py` (1 Finding constructor, description line ~409, fix line ~414)
- AVS → `src/drift/signals/architecture_violation.py` — **no changes, already exempt**

**Finding fields** (from data-model.md): `description` = reason field; `fix` = next_action field

---

## Phase 1: Setup

**Purpose**: Create the test file skeleton before any implementation.

- [X] T001 Create `tests/test_finding_message_quality.py` with `FAMILY_A` and `FAMILY_B` keyword constant lists and a `passes_keyword_check(text: str) -> bool` helper that returns `True` when any keyword from either family appears in `text.lower()` (substring match)

---

## Phase 2: Foundational — Write ALL Failing Smoke-Check Tests (TDD RED)

**Purpose**: Implement all smoke-check test functions **before** any signal strings are changed. Every test MUST fail at this point (current strings contain no layer/concern or change-implication keywords). This is the RED phase required by Constitution Principle II.

**⚠️ CRITICAL**: No user story edits to signal files until T004 (ALL tests confirmed failing).

- [X] T002 Add failing `description` smoke-check test functions in `tests/test_finding_message_quality.py` — one per signal (PFS, MDS exact-dup, MDS near-dup, EDS): each invokes the signal's `analyze()` on minimal synthetic input (or constructs Finding directly with current template output), then asserts `passes_keyword_check(finding.description)` — currently fails for all four
- [X] T003 Add failing `fix` smoke-check test functions in `tests/test_finding_message_quality.py` — one per signal (PFS, MDS exact-dup, MDS near-dup, EDS): each asserts `passes_keyword_check(finding.fix)` on the current fix string — currently fails for all four
- [X] T004 Run `python -m pytest tests/test_finding_message_quality.py -v --tb=short` → verify ALL 8 test functions FAIL with `AssertionError` (RED phase confirmed; do not proceed until all fail)

**Checkpoint**: Failing tests exist for every required assertion — implementation can now begin per user story.

---

## Phase 3: User Story 1 — Boundary-Aware Finding Description (Priority: P1) 🎯 MVP

**Goal**: Every `description` string produced by PFS, MDS, and EDS names either a concrete responsibility boundary/concern or a change implication — so a developer can identify the violated boundary from the finding text alone.

**Independent Test**: `python -m pytest tests/test_finding_message_quality.py -k "description" -v` — all description tests pass.

- [X] T005 [P] [US1] Update `description` f-string in the PFS Finding constructor at `src/drift/signals/pattern_fragmentation.py` (~line 459) to include: name of the shared responsibility concern the fragmented patterns represent AND an indication that inconsistency spreads change risk across the module
- [X] T006 [P] [US1] Update `description` strings in both MDS Finding constructors in `src/drift/signals/mutant_duplicates.py`: exact-duplicate constructor (~line 425) — add responsibility-boundary and change-propagation language; near-duplicate constructor (~line 604) — add responsibility-boundary and coupled-change-risk language
- [X] T007 [P] [US1] Update `description` f-string in the EDS Finding constructor at `src/drift/signals/explainability_deficit.py` (~line 409) to include: naming the responsibility boundary that the opaque function obscures AND a statement that callers cannot determine ownership or expected change scope
- [X] T008 [US1] Run `python -m pytest tests/test_finding_message_quality.py -k "description" -v` → confirm all 4 description tests PASS (GREEN); if any fail, revise the corresponding string until it passes

**Checkpoint**: US1 complete — all `description` fields name a boundary or change implication; tests green.

---

## Phase 4: User Story 2 — Change-Cost Transparency in Fix String (Priority: P2)

**Goal**: Every `fix` string produced by PFS, MDS, and EDS names at least one concrete category of follow-up change that becomes harder or more expensive if the finding is not addressed.

**Independent Test**: `python -m pytest tests/test_finding_message_quality.py -k "fix" -v` — all fix tests pass.

- [X] T009 [P] [US2] Update `fix` f-string in the PFS Finding constructor at `src/drift/signals/pattern_fragmentation.py` (~line 446) to name the change category that fragmentation makes expensive (e.g., every variant must be updated separately for cross-cutting changes; update effort scales with variant count)
- [X] T010 [P] [US2] Update `fix` strings in both MDS Finding constructors in `src/drift/signals/mutant_duplicates.py`: exact-duplicate fix (~line 434) — add boundary framing identifying which concern owns the extracted helper; near-duplicate fix (~line 611) — add change-coupling language (diverged copies require coupled changes at each occurrence)
- [X] T011 [P] [US2] Update `fix` f-string in the EDS Finding constructor at `src/drift/signals/explainability_deficit.py` (~line 414) to name the change category that undocumented complexity makes expensive (e.g., callers cannot safely change behaviour without risk of violating hidden contracts); preserve existing missing-item list
- [X] T012 [US2] Run `python -m pytest tests/test_finding_message_quality.py -k "fix" -v` → confirm all 4 fix tests PASS (GREEN); if any fail, revise the corresponding string until it passes

**Checkpoint**: US2 complete — all `fix` fields name a concrete change category; tests green.

---

## Phase 5: User Story 3 — Consistent Boundary Vocabulary in SKILL.md (Priority: P3)

**Goal**: The finding-message-authoring SKILL provides a shared vocabulary reference so that boundary and change-cost terms are consistent across signals reviewed or authored in the future.

**Independent Test**: `.github/skills/drift-finding-message-authoring/SKILL.md` contains a "Boundary Vocabulary" section with Family A and Family B term lists.

- [X] T013 [US3] Add a "Boundary Vocabulary" section to `.github/skills/drift-finding-message-authoring/SKILL.md` listing Family A (layer/concern terms: `layer`, `boundary`, `service`, `interface`, `concern`, `responsibility`, `domain`, `ownership`, `contract`) and Family B (change-implication terms: `change propagation`, `coupled`, `change risk`, `isolat`, `expensive`, `spread`, `ripple`, `entangled`, `effort`) as the recommended vocabulary for reason and next_action strings in new and updated signal findings

**Checkpoint**: US3 complete — vocabulary section present and reviewable.

---

## Final Phase: Polish & Verification

**Purpose**: Verify no regressions, lint clean, and type-correct after all edits.

- [X] T014 Run full quick test suite → `python -m pytest tests/ --ignore=tests/test_smoke_real_repos.py -m "not slow" -q -n auto --dist=loadscope` → confirm no regressions in any other signal or output test
- [X] T015 [P] Run ruff on modified signal files → `ruff check src/drift/signals/pattern_fragmentation.py src/drift/signals/mutant_duplicates.py src/drift/signals/explainability_deficit.py` → zero violations
- [X] T016 [P] Run mypy on modified signal files → `mypy src/drift/signals/pattern_fragmentation.py src/drift/signals/mutant_duplicates.py src/drift/signals/explainability_deficit.py` → zero type errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story edits to signal files
- **Phase 3 (US1)**: Depends on Phase 2 completion (all tests confirmed failing)
- **Phase 4 (US2)**: Depends on Phase 2 completion; can run in parallel with Phase 3 (different fields in same constructors, but careful: same files — sequence after Phase 3 to avoid merge conflicts)
- **Phase 5 (US3)**: Depends on Phase 2 completion; touches a different file, can run in parallel with Phase 3+4
- **Final Phase**: Depends on all user story phases complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — independently testable via description tests
- **US2 (P2)**: Can start after Foundational — but edits same files as US1 (different fields); best done after US1 to avoid conflicts
- **US3 (P3)**: Independent of US1 and US2 — touches only SKILL.md

### Within Each User Story

- Tests were written (Phase 2) and confirmed failing **before** implementation
- T005, T006, T007 touch different files → can run in parallel
- T009, T010, T011 touch different files → can run in parallel
- Within MDS (T006 / T010): both constructors are in the same file → sequential within that task

### Parallel Opportunities

Within Phase 3: T005, T006, T007 (different files — can be implemented by separate developers)
Within Phase 4: T009, T010, T011 (different files — can be implemented by separate developers)
T013 (US3): can run in parallel with any Phase 3/4 task (different file)
T015, T016 (Final Phase): can run in parallel with each other

---

## Parallel Example: User Story 1

```bash
# Three developers in parallel once Phase 2 is complete:
Dev A: T005 — update pattern_fragmentation.py description
Dev B: T006 — update mutant_duplicates.py descriptions (both constructors)
Dev C: T007 — update explainability_deficit.py description
# Then all three converge on T008 to run the description tests
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational — write failing tests (T002–T004)
3. Complete Phase 3: User Story 1 — description strings (T005–T008)
4. **STOP and VALIDATE**: Run `pytest tests/test_finding_message_quality.py -k "description"` → green
5. This is the MVP: every PFS/MDS/EDS finding now names a responsibility boundary

### Incremental Delivery

1. T001–T004 → Test skeleton ready, all failing
2. T005–T008 → US1 complete, descriptions enriched (MVP)
3. T009–T012 → US2 complete, fix strings enriched
4. T013 → US3 complete, vocabulary documented
5. T014–T016 → Full suite clean, ship

---

## Summary

| Metric | Value |
|---|---|
| Total tasks | 16 |
| Phase 2 (Foundational tests) | 3 tasks |
| US1 tasks | 4 tasks (3 signal edits + 1 verify) |
| US2 tasks | 4 tasks (3 signal edits + 1 verify) |
| US3 tasks | 1 task |
| Final phase tasks | 3 tasks |
| Parallel opportunities | T005‖T006‖T007 and T009‖T010‖T011 and T013‖any US phase |
| MVP scope | T001–T008 (Phase 1 + 2 + 3 = US1 complete) |
| Files changed | 3 signal files + 1 new test file + 1 SKILL.md |
| Finding constructors edited | 4 (PFS×1, MDS×2, EDS×1) |
| AVS changes | None (exempt) |
