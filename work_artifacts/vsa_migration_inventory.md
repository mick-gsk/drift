# VSA Migration Inventory — ADR-100 Monorepo Capability Split

**Status:** In Progress  
**Last Updated:** 2026-05-02  
**ADR Reference:** [ADR-100](../docs/decisions/ADR-100-uv-workspace-monorepo.md)

## Overview

This inventory tracks the Vertical Slice Architecture (VSA) migration of the drift
monolith into discrete capability packages under `packages/`. Each package corresponds
to a bounded capability slice with its own `pyproject.toml`, canonical source tree, and
test suite.

---

## Capability Packages (Completed)

| Package | Namespace | Phase | Status | Source |
|---------|-----------|-------|--------|--------|
| `drift` | `drift` | meta | ✅ complete | `packages/drift/` |
| `drift-engine` | `drift_engine` | 1 | ✅ complete | `packages/drift-engine/` |
| `drift-config` | `drift_config` | 2 | ✅ complete | `packages/drift-config/` |
| `drift-sdk` | `drift_sdk` | 3a | ✅ complete | `packages/drift-sdk/` |
| `drift-output` | `drift_output` | 3b | ✅ complete | `packages/drift-output/` |
| `drift-verify` | `drift_verify` | 3c | ✅ complete | `packages/drift-verify/` |
| `drift-session` | `drift_session` | 4b | ✅ complete | `packages/drift-session/` |
| `drift-mcp` | `drift_mcp` | 5a | ✅ complete | `packages/drift-mcp/` |
| `drift-cli` | `drift_cli` | 5b | ✅ complete | `packages/drift-cli/` |
| `drift-cockpit` | `drift_cockpit` | 6 | ✅ complete | `packages/drift-cockpit/` |

## Frontend / Non-Python Packages

| Package | Technology | Status |
|---------|-----------|--------|
| `cockpit-ui` | Next.js / TypeScript | ✅ in workspace |
| `drift-analyzer-sdk` | TypeScript | ✅ in workspace |

---

## Legacy Compatibility Layer (`src/drift/`)

The `src/drift/` tree serves as a **compatibility re-export layer** during the migration
transition period. All modules under `src/drift/` that have been migrated to canonical
packages MUST be compat stubs (re-exporting from the canonical package namespace).

### Compat-Layer Audit Results

Run `scripts/migration/audit_legacy_paths.py --json --repo .` for the current state.
Run `scripts/migration/check_import_boundaries.py --json --repo .` to check for boundary violations.

| Metric | Value |
|--------|-------|
| Total compat stubs | 0 (all resolved via `packages/drift/`) |
| Violations | 0 |
| Orphaned stubs | 0 |

---

## Canonical Package Namespaces

The following canonical namespaces are in use. `src/drift/` compat stubs **must not**
import from these namespaces directly.

```
drift_engine   drift_cli     drift_config
drift_sdk      drift_session drift_mcp
drift_output   drift_verify
```

---

## Phases Summary

| Phase | Description | PR / Commit | Status |
|-------|-------------|-------------|--------|
| 1 | `drift-engine` — signal pipeline, scoring | — | ✅ |
| 2 | `drift-config` — DriftConfig, loader | — | ✅ |
| 3a | `drift-sdk` — public SDK surface | — | ✅ |
| 3b | `drift-output` — JSON/Rich/guided output | — | ✅ |
| 3c | `drift-verify` — verification engine | — | ✅ |
| 4b | `drift-session` — session/outcome/reward/ledger | PR #576 | ✅ |
| 5a | `drift-mcp` — MCP server and all 16 router modules | PR #576 | ✅ |
| 5b | `drift-cli` — 50 CLI command modules | PR #576 | ✅ |
| 6 | `drift-cockpit` — decision cockpit | — | ✅ |
| 7a | Cleanup: mypy/vulture paths, tmp files, CI hygiene | PR #576 | ✅ |

---

## Remaining Work (Phase 6+)

- Phase 6b: GitHub Actions path-filter updates for per-package CI scoping
- Phase 6c: DEVELOPER.md and guard-skill cleanup for new package layout
- Full removal of `src/drift/` compat layer (post-stabilization)

---

## Verification Commands

```bash
# Audit compat stubs
python scripts/migration/audit_legacy_paths.py --json --repo .

# Check import boundaries
python scripts/migration/check_import_boundaries.py --json --repo .

# Run migration contract tests
python -m pytest tests/migration/ -v
```
