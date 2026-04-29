# Data Model: findings-change-effort-coupling

**Phase 1 output** | Feature: `009-findings-change-effort-coupling`

---

## Overview

This feature makes **no structural changes** to the `Finding` data model. All changes are confined to the string content of two existing fields in the `Finding` dataclass defined in `src/drift/models/_findings.py`.

---

## Finding Field Mapping

| Finding field | SKILL.md conceptual term | Type | Change scope |
|---|---|---|---|
| `description` | `reason` | `str` | Content update in 4 signal files |
| `fix` | `next_action` | `str \| None` | Content update in 4 signal files |
| All other fields | — | various | **Unchanged** |

The SKILL.md for `drift-finding-message-authoring` uses the terms `reason` and `next_action`. These are conceptual names. The actual Python field names are `description` and `fix`.

---

## Per-Signal Change Inventory

### PFS — `src/drift/signals/pattern_fragmentation.py`

| Sub-finding | Field | Current content pattern | Required enrichment |
|---|---|---|---|
| Pattern fragmentation | `description` | `"{N} {category} variants in {path}/ ({canonical_count}/{total} use canonical pattern)."` | Add: responsibility boundary statement — what shared concern the fragmented patterns represent; why inconsistency increases change-coupling across the module. |
| Pattern fragmentation | `fix` | `"Consolidate to the dominant pattern ({N}x, exemplar: {ref}). Deviations: {list}."` | Add: change-cost implication — why inconsistent patterns make future edits more expensive (each variant must be tracked separately). |

**Finding constructors to edit**: 1 (line ~459 in current HEAD)

---

### AVS — `src/drift/signals/architecture_violation.py`

| Sub-finding | Field | Current content | Assessment |
|---|---|---|---|
| Upward layer import | `description` | Names layers (data/infrastructure, presentation/API) | **Exempt** — already names concrete layers |
| Upward layer import | `fix` | Names "service layer or abstraction interface" | **Exempt** |
| Policy boundary violation | `description` | Names "boundary rule '{name}'" | **Exempt** — names the concern/boundary |
| Policy boundary violation | `fix` | Names "service layer or interface" | **Exempt** |
| All AVS variants | both | See research.md Decision 2 | **No changes required** |

**Finding constructors to edit**: 0

---

### MDS — `src/drift/signals/mutant_duplicates.py`

| Sub-finding | Field | Current content pattern | Required enrichment |
|---|---|---|---|
| Exact duplicate | `description` | `"{N} identical copies ({loc} lines each) at: {locations}. Consider consolidating."` | Add: shared responsibility boundary — what concern these copies represent; how divergence creates a change-propagation risk (one fix must be applied in N places). |
| Exact duplicate | `fix` | `"Extract {name}() into {parent}/shared.py. {N} identical copies. Effort: S."` | Retain `Effort: S`; add: boundary framing — shared concern that owns this logic. |
| Near-duplicate | `description` | `"...are {sim:.0%} similar. Small differences may indicate copy-paste divergence."` | Add: change-coupling implication — diverged copies force coupled changes; point to the responsibility boundary that should own the canonical version. |
| Near-duplicate | `fix` | `"Extract ... Similarity: {sim:.0%}. Effort: {effort}."` | Add: boundary context for where the shared version belongs. |

**Finding constructors to edit**: 2 (lines ~425, ~604 in current HEAD)

---

### EDS — `src/drift/signals/explainability_deficit.py`

| Sub-finding | Field | Current content pattern | Required enrichment |
|---|---|---|---|
| Unexplained complexity | `description` | `"Complexity: {N}, LOC: {N}. No docstring. No test. No return type."` | Add: responsibility boundary implication — high-complexity functions without documentation define an opaque responsibility; callers cannot determine ownership or expected change scope. |
| Unexplained complexity | `fix` | `"Function {name} (complexity {N}): add {missing}."` or `None` | When present: add change-cost framing — undocumented complex functions accumulate hidden change cost by obscuring which caller assumptions are guaranteed. |

**Finding constructors to edit**: 1 (line ~404 in current HEAD)

---

## Unchanged Data Model

The following model elements are **not modified** by this feature:

- `Finding` dataclass structure (`src/drift/models/_findings.py`)
- `SignalType` enum (`src/drift/models/_enums.py`)
- `Severity` enum
- `RepoAnalysis`, `AgentAction`, `AgentTelemetry` models
- JSON schema (`drift.output.schema.json`)
- SARIF schema
- Any output formatter (`rich_output.py`, `json_output.py`, `sarif_output.py`)
- Any scoring module (`src/drift/scoring/`)
- CLI commands (`src/drift/commands/`)

---

## State Transition Diagram

This feature has no state machines. There are no new transitions.

```
[Existing Finding.description] --(string content update)--> [Enriched Finding.description]
[Existing Finding.fix]         --(string content update)--> [Enriched Finding.fix]
```

All other fields remain in their current state throughout signal execution.
