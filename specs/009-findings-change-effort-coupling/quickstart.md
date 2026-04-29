# Quickstart: findings-change-effort-coupling

**Phase 1 output** | Feature: `009-findings-change-effort-coupling`

---

## Overview

This feature updates `description` and `fix` string fields in three signal files. The key verification step is running the finding message quality smoke-check tests.

---

## Running the Smoke-Check Tests

```bash
# Fast: run only the new quality smoke-check tests
.venv/Scripts/python.exe -m pytest tests/test_finding_message_quality.py -v --tb=short

# Full quick suite (excludes slow/smoke real-repo tests)
.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_smoke_real_repos.py \
  -m "not slow" -q
```

Expected output: all tests pass, no `AssertionError: description is pattern-only`.

---

## Verifying a Signal Update

To check that a specific signal's updated description passes the keyword contract:

```python
# In a Python REPL or scratch script
from pathlib import Path
FAMILY_A = ["layer", "boundary", "service", "interface", "concern",
            "responsibility", "domain", "ownership", "contract"]
FAMILY_B = ["change propagation", "coupled", "change risk", "isolat",
            "expensive", "spread", "ripple", "entangled", "effort"]

def passes_keyword_check(description: str) -> bool:
    d = description.lower()
    return any(t in d for t in FAMILY_A) or any(t in d for t in FAMILY_B)

# Example: test a proposed PFS description
passes_keyword_check(
    "3 error_handling variants in src/drift/signals/ "
    "(2/3 use canonical pattern). Inconsistency spreads change risk: "
    "each variant must be updated separately when the shared concern evolves."
)
# → True  (Family B hit: "change risk", "spreads")
```

---

## Files Changed by This Feature

| File | Change type |
|---|---|
| `src/drift/signals/pattern_fragmentation.py` | Edit `description` and `fix` string templates |
| `src/drift/signals/mutant_duplicates.py` | Edit `description` and `fix` string templates (2 Finding constructors) |
| `src/drift/signals/explainability_deficit.py` | Edit `description` and `fix` string templates |
| `tests/test_finding_message_quality.py` | **New file** — keyword smoke-check tests |
| `.github/skills/drift-finding-message-authoring/SKILL.md` | Add "Boundary Vocabulary" section |
| `src/drift/signals/architecture_violation.py` | **Not changed** — already exempt |

---

## Development Order (TDD)

Per Constitution Principle II (Test-First):

1. **Write failing tests first** in `tests/test_finding_message_quality.py`
2. Run tests → confirm they fail (existing strings don't contain keywords)
3. Update signal description/fix strings (3 files)
4. Run tests → confirm they pass
5. Run full quick suite to confirm no regressions

---

## Checking Drift Self-Analysis

To confirm the updated findings appear correctly in drift's own scan:

```bash
.venv/Scripts/python.exe -m drift analyze --repo . --format rich
# Look for PFS / MDS / EDS findings and verify the description text
# contains boundary/change-cost language
```

No score changes are expected — only finding text changes.
