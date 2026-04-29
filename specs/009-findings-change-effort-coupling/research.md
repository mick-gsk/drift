# Research: findings-change-effort-coupling

**Phase 0 output** | Feature: `009-findings-change-effort-coupling`

---

## Decision 1: Signal-to-file mapping for PFS / AVS / MDS / EDS

**Decision**: The four mandatory abbreviations map to the following source files and SignalType enum values:

| Abbreviation (spec) | Full name (spec) | SignalType enum value | Source file |
|---|---|---|---|
| PFS | Pattern Fragmentation Score | `PATTERN_FRAGMENTATION` | `src/drift/signals/pattern_fragmentation.py` |
| AVS | Abstraction Violation Score | `ARCHITECTURE_VIOLATION` | `src/drift/signals/architecture_violation.py` |
| MDS | Module Dependency Score | `MUTANT_DUPLICATE` | `src/drift/signals/mutant_duplicates.py` |
| EDS | Entanglement Depth Score | `EXPLAINABILITY_DEFICIT` | `src/drift/signals/explainability_deficit.py` |

**Rationale**: Confirmed by reading guard skill descriptions (guard-src-drift SKILL.md table rows for AVS/EDS/MDS/PFS with matching human-readable descriptions) and inspecting each signal file's Finding title.

**Note**: The spec's conceptual names ("Module Dependency Score", "Entanglement Depth Score") are user-facing shorthand. The codebase uses "Mutant Duplicate" and "Explainability Deficit" respectively. The mapping is unambiguous from guard skill context.

---

## Decision 2: Current description/fix texts and "pattern-only" assessment

**Decision**: Only PFS, MDS (exact duplicate sub-case), and EDS require updates. AVS findings are largely exempt.

### PFS — `pattern_fragmentation.py` line 376 + 446

Current description template:
```
"{num_variants} {category.value} variants in {module_path}/ ({canonical_count}/{total} use canonical pattern)."
```
Optional second line: framework-calibration note.
Optional lines: up to 3 non-canonical instance refs.

Current fix template:
```
"Consolidate to the dominant pattern ({canonical_count}x, exemplar: {instance_ref}). Deviations: {deviations}."
```

**Assessment**: `category.value` names a structural category (e.g., `error_handling`, `API_ENDPOINT`), not a layer/concern or change implication. The fix says "consolidate" but does not name the responsibility boundary or change-cost. → **Pattern-only by SC-003: update required.**

### AVS — `architecture_violation.py` lines 637–650, 739–752

Current description (upward import):
```
"{src}:{line} — data/infrastructure layer imports from presentation/API layer. Expected direction: presentation → service → data."
```
Current description (policy boundary):
```
"{file}:{line} imports '{module}' which violates boundary rule '{name}' (deny: {pattern})"
```
Current fix (upward import): `"Move {dst.name} logic behind a service layer or abstraction interface..."`
Current fix (policy): `"Remove import '{module}'... Route access through a service layer or interface."`

**Assessment**: All AVS finding variants already name concrete layers (data, infrastructure, presentation, API, service) and/or named boundary rules. Per SC-003, presence of either layer/concern OR change implication is sufficient to be exempt. → **AVS findings are exempt; no required update.**

### MDS — `mutant_duplicates.py` lines 398–434, 604–622

Current description (exact duplicate):
```
"{n} identical copies ({loc} lines each) at: {locations}. Consider consolidating."
```
Current fix (exact duplicate):
```
"Extract {name}() into {common_parent}/shared.py. {n} identical copies. Effort: S."
```
Current description (near-duplicate):
```
"{a_path}:{line} and {b_path}:{line} are {sim:.0%} similar. Small differences may indicate copy-paste divergence."
```
Current fix (near-duplicate):
```
"Extract ... Similarity: {sim:.0%}. Effort: {effort}."
```

**Assessment**:
- Exact duplicate description: names neither layer/concern nor change implication → **update required**.
- Exact duplicate fix: `"Effort: S"` is a size code (not a change-risk or boundary statement), `"Consider consolidating"` is generic. → **update required**.
- Near-duplicate description: "copy-paste divergence" hints at a change pattern but does not name the shared responsibility boundary → **update required**.
- Near-duplicate fix: "Effort: {effort}" is a size code → same as above, needs change-risk framing.

### EDS — `explainability_deficit.py` lines 360–414

Current description:
```
"Complexity: {N}, LOC: {N}. No docstring. No corresponding test found. No return type annotation."
```
Current fix:
```
"Function {name} (complexity {N}): add {Docstring, Tests, Return-Type}."
```

**Assessment**: Purely metric/structural — names no layer, no concern, no change implication. → **Pattern-only by SC-003: update required.**

---

## Decision 3: Keyword reference list for smoke-check tests (SC-005)

**Decision**: Smoke-check tests assert substring presence using the following two keyword families. A finding is considered **not pattern-only** if its `description` field contains at least one term from either family.

### Family A — Layer/Concern terms
```
layer, boundary, service, interface, concern, responsibility, module boundary,
domain, ownership, contract
```

### Family B — Change-implication terms
```
change propagation, coupled, change risk, isolate, isolation, expensive,
spread, ripple, entangled, effort
```

**Rationale**: SC-005 requires keyword smoke-checks (substring, not exact-string match) per signal. The reference list covers the vocabulary recommended in `drift-finding-message-authoring/SKILL.md` (boundary terms section to be added). Both families are needed because SC-003 requires either a layer/concern OR a change implication.

**Test location**: `tests/test_finding_message_quality.py` (new file). Each test constructs a synthetic in-memory fixture (a `list[ParseResult]` or equivalent input) or uses ground-truth fixture helpers, runs the signal's `analyze()`, and asserts the keyword presence in every returned `Finding.description`.

---

## Decision 4: Output format propagation

**Decision**: No format adapter changes required.

**Rationale**: `Finding.description` and `Finding.fix` are `str | None` fields. Rich, JSON, and SARIF output renderers consume them as opaque strings. Any change to the string content propagates automatically through all output formats. Verified by inspecting:
- `src/drift/output/rich_output.py` (renders `finding.description` and `finding.fix` directly)
- `src/drift/output/json_output.py` (serializes all Finding fields via Pydantic)
- JSON/SARIF schema: `drift.output.schema.json` defines `description` and `fix` as `string | null`

**Alternatives considered**: Adding a structured `boundary_context` field to Finding was considered. Rejected because (a) it requires a model change + migration for all 24+ signals, (b) spec clarification Q4 confirmed automatic format propagation without structural changes, (c) YAGNI — the string fields are sufficient for the use cases.

---

## Decision 5: SKILL.md vocabulary section placement

**Decision**: Add a "Boundary Vocabulary" section to `.github/skills/drift-finding-message-authoring/SKILL.md` as a non-normative reference list. It is not enforced by a merge gate (spec clarification Q3 answer: SKILL.md guidance, not a hard gate).

**Rationale**: The vocabulary serves as a shared reference for implementers and reviewers when deciding whether a proposed description already satisfies SC-003. Governance is via code review, not automated gating.

---

## Resolved Unknowns

| NEEDS CLARIFICATION item | Resolution |
|---|---|
| Which file implements MDS? | `mutant_duplicates.py` (MUTANT_DUPLICATE) — confirmed from guard skill table |
| Which file implements EDS? | `explainability_deficit.py` (EXPLAINABILITY_DEFICIT) — confirmed from guard skill description "Unexplained Complexity" |
| Are AVS findings already exempt? | Yes — all AVS variants name concrete layers or named boundary rules; no required changes |
| How many Finding constructors need changes? | PFS: 1 (line 459), MDS: 2 (lines 425, 604), EDS: 1 (line 404) |
| Do tests need fixture-level setup? | No — direct synthetic input sufficient; full fixture machinery not required for smoke-checks |
