# Finding Message Quality Contract

**Contract type**: Output quality gate for signal `description` and `fix` fields  
**Scope**: Signals PFS, MDS, EDS (mandatory); AVS exempt (see research.md Decision 2)  
**Enforcement**: Keyword smoke-check tests in `tests/test_finding_message_quality.py`

---

## Contract Definition

A Finding produced by PFS, MDS, or EDS MUST NOT be "pattern-only" after this feature is implemented.

### Operative Definition of "Pattern-Only" (SC-003)

A `description` (reason) string is **pattern-only** when it names:
- **neither** a concrete layer, concern, or responsibility boundary
- **nor** any change implication

Presence of **either one** is sufficient to make the finding **not pattern-only**.

### Keyword Families for Smoke-Checks (SC-005)

Smoke-checks use substring matching (case-insensitive). A finding passes if its `description` contains at least one term from at least one family.

**Family A — Layer/Concern terms**:
```
layer, boundary, service, interface, concern, responsibility,
module boundary, domain, ownership, contract
```

**Family B — Change-implication terms**:
```
change propagation, coupled, change risk, isolat, expensive,
spread, ripple, entangled, effort
```

---

## Per-Signal Acceptance Criteria

### PFS (`pattern_fragmentation.py`)

| Check | Condition | Pass criterion |
|---|---|---|
| `description` not pattern-only | Every PFS Finding | Contains ≥1 term from Family A or Family B |
| `fix` not pattern-only | Every PFS Finding | Contains ≥1 term from Family A or Family B |

### MDS (`mutant_duplicates.py`)

| Check | Condition | Pass criterion |
|---|---|---|
| Exact duplicate `description` not pattern-only | `Finding.title` starts with "Exact duplicates" | Contains ≥1 term from Family A or Family B |
| Near-duplicate `description` not pattern-only | `Finding.title` starts with "Near-duplicate" | Contains ≥1 term from Family A or Family B |

### EDS (`explainability_deficit.py`)

| Check | Condition | Pass criterion |
|---|---|---|
| `description` not pattern-only | Every EDS Finding | Contains ≥1 term from Family A or Family B |

---

## What This Contract Does NOT Cover

- Exact wording of enriched strings (free-form authoring)
- The `fix` field for AVS (exempt — already names layers/boundaries)
- Any output format adapter (propagation is automatic)
- SKILL.md vocabulary compliance (review-time guidance, not automated)
- Signal detection logic (scores, thresholds, metadata)

---

## Test File Location

`tests/test_finding_message_quality.py`

This file uses lightweight synthetic fixtures: minimal `ParseResult`-equivalent inputs are constructed in-memory for each signal, the signal's `analyze()` method is called, and every returned Finding is checked against the keyword families above.

Alternatively, where synthetic fixture construction is complex, tests may patch internal finding-builder helpers to return a known `description` and verify the enrichment is present in realistic format strings.
