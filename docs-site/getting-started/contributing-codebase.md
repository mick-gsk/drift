# Contributing to the Drift Codebase — Package Capability Guide

> **Quick rule**: Edit canonical capability packages (`packages/drift-*/src/drift_*/`), never the compat layer (`packages/drift/src/drift/`).

---

## Package-to-Capability Map

Before making any change, find the right package:

| If you want to change... | Edit this package | Namespace |
|---|---|---|
| A detection signal (PFS, AVS, MDS, etc.) | `packages/drift-engine/src/drift_engine/signals/` | `drift_engine.signals` |
| Ingestion / file discovery / AST parsing | `packages/drift-engine/src/drift_engine/ingestion/` | `drift_engine.ingestion` |
| Scoring weights or severity gating | `packages/drift-engine/src/drift_engine/scoring/` | `drift_engine.scoring` |
| A CLI command (`drift analyze`, `drift brief`, etc.) | `packages/drift-cli/src/drift_cli/commands/` | `drift_cli.commands` |
| Configuration schema or defaults | `packages/drift-config/src/drift_config/` | `drift_config` |
| The public Python SDK (`scan`, `check`, etc.) | `packages/drift-sdk/src/drift_sdk/api/` | `drift_sdk.api` |
| Data models (`Finding`, `RepoAnalysis`, etc.) | `packages/drift-sdk/src/drift_sdk/models/` | `drift_sdk.models` |
| Session state or outcome tracking | `packages/drift-session/src/drift_session/` | `drift_session` |
| MCP server tools or router dispatch | `packages/drift-mcp/src/drift_mcp/` | `drift_mcp` |
| Output renderers (Rich, JSON, SARIF) | `packages/drift-output/src/drift_output/` | `drift_output` |

---

## Step-by-Step Guide for Making a Change

1. **Identify the capability** from the table above.
2. **Navigate to the canonical package**: `packages/drift-<capability>/src/drift_<capability>/`
3. **Edit the canonical file** — never touch `packages/drift/src/drift/` for logic changes.
4. **Run the relevant tests**: `pytest tests/test_<signal_abbrev>*.py -q --tb=short`
5. **Run migration regression tests**: `pytest tests/migration/ -q`
6. **Run full check**: `make check`

---

## The Compat Layer — What It Is and Isn't

`packages/drift/src/drift/` is the **compatibility re-export layer**. It makes `from drift.signals import X` work by aliasing to `drift_engine.signals`.

- ✅ **Read it** to understand the public API surface.
- ❌ **Do not add implementation here.** Only re-export stubs (`sys.modules` aliasing or `__path__` redirects) are allowed.
- ❌ **Do not edit it for logic fixes.** Find the canonical package instead.

---

## FAQ

**Q: Where is the `PatternFragmentation` signal implemented?**
A: `packages/drift-engine/src/drift_engine/signals/pattern_fragmentation.py`

**Q: I imported `from drift.signals import X` — where does that resolve?**
A: To `packages/drift-engine/src/drift_engine/signals/` via compat stub aliasing.

**Q: Can I add a new file to `src/drift/`?**
A: No. `src/drift/` is fully superseded and must contain zero `.py` files.

**Q: Why does `packages/drift/src/drift/` exist at all?**
A: Backward compatibility. External code that imports `drift.*` continues to work without changes.

**Q: How do I verify boundary compliance?**
A:
```bash
python scripts/migration/audit_legacy_paths.py   # Check compat layer
python scripts/migration/check_import_boundaries.py  # Check canonical packages
pytest tests/migration/ -q  # Run all boundary regression tests
```

---

## Architecture Reference

Full boundary rules and package hierarchy: [docs/architecture/vsa-monorepo.md](../../docs/architecture/vsa-monorepo.md)
