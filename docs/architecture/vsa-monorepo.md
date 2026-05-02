# VSA Monorepo — Canonical Capability Architecture

**ADR-100 / ADR-102 — Vertical Slice Architecture Migration**

This document is the authoritative reference for capability ownership in the Drift monorepo.

---

## Canonical Capability Packages

| Package | Install name | Namespace | Capability |
|---|---|---|---|
| `packages/drift-engine` | `drift-engine` | `drift_engine` | Signals, ingestion, scoring, pipeline |
| `packages/drift-cli` | `drift-cli` | `drift_cli` | Click CLI subcommands |
| `packages/drift-config` | `drift-config` | `drift_config` | Config schema, profile detection, path overrides |
| `packages/drift-sdk` | `drift-sdk` | `drift_sdk` | Public Python SDK, MCP tool API |
| `packages/drift-session` | `drift-session` | `drift_session` | Session state, outcome tracking, reward chain |
| `packages/drift-mcp` | `drift-mcp` | `drift_mcp` | MCP server (FastMCP), router dispatch |
| `packages/drift-output` | `drift-output` | `drift_output` | Rich terminal, JSON, SARIF output renderers |
| `packages/drift-verify` | `drift-verify` | `drift_verify` | Verification pipeline |
| `packages/drift` | `drift-analyzer` | `drift` | Compat meta-package: re-exports all above |

---

## Import Flow

```
External user code / tests
        │  from drift.signals import X
        ▼
  packages/drift/src/drift/        ← compat layer (re-exports, read-only)
  e.g. drift.signals → sys.modules alias to drift_engine.signals
        │
        ▼
  packages/drift-engine/src/drift_engine/signals/   ← canonical implementation
```

### How re-export stubs work

```python
# packages/drift/src/drift/signals/__init__.py
import importlib, sys
sys.modules[__name__] = importlib.import_module("drift_engine.signals")
# Result: drift.signals IS drift_engine.signals (same module object)
```

---

## Boundary Rules

**Rule 1 — No active implementation in compat layer.**
`packages/drift/src/drift/` must only contain re-export stubs (`sys.modules` aliasing or
`__path__` redirects). No business logic, no classes, no algorithms.

**Rule 2 — Leftward-only imports.**
Lower-layer packages (engine, config) must not import from higher-level packages (cli, mcp,
output, sdk). Information flows upward.

**Rule 3 — No legacy imports from canonical packages.**
`packages/drift-*/` source code must not import from `src.drift.*`. The compat namespace
`drift.*` is allowed (it resolves to canonical packages via stubs).

**Rule 4 — No active implementation in src/drift/.**
`src/drift/` must contain zero `.py` files (only empty `__pycache__` subdirs). This directory
is fully superseded by `packages/drift/src/drift/` as the compat layer.

---

## Directory Layout

```
packages/
├── drift/                          # compat meta-package (re-exports only)
│   └── src/drift/
│       ├── __init__.py             # re-exports, __path__ redirect
│       ├── signals/                # → drift_engine.signals
│       ├── commands/               # → drift_cli.commands
│       ├── config/                 # → drift_config
│       ├── api/                    # → drift_sdk.api
│       ├── session.py              # → drift_session.session
│       ├── mcp_server.py           # → drift_mcp.mcp_server
│       └── output/                 # → drift_output
├── drift-engine/                   # CANONICAL: signals, scoring, ingestion
├── drift-cli/                      # CANONICAL: CLI subcommands
├── drift-config/                   # CANONICAL: configuration
├── drift-sdk/                      # CANONICAL: public API + models
├── drift-session/                  # CANONICAL: session + outcome tracking
├── drift-mcp/                      # CANONICAL: MCP server + router
├── drift-output/                   # CANONICAL: output renderers
└── drift-verify/                   # CANONICAL: verification pipeline

src/drift/                          # LEGACY: empty (only __pycache__ remains)
```

---

## Verification Commands

```bash
# Check for active implementation in compat layer
python scripts/migration/audit_legacy_paths.py

# Check for import boundary violations
python scripts/migration/check_import_boundaries.py

# Run all migration regression tests
pytest tests/migration/ -v

# Combined check
pytest tests/migration/ -q && python scripts/migration/check_import_boundaries.py
```

---

## Migration Status

| Area | State | Notes |
|------|-------|-------|
| `src/drift/` signals | ✅ Migrated | → `drift_engine.signals` |
| `src/drift/` ingestion | ✅ Migrated | → `drift_engine.ingestion` |
| `src/drift/` scoring | ✅ Migrated | → `drift_engine.scoring` |
| `src/drift/` commands | ✅ Migrated | → `drift_cli.commands` |
| `src/drift/` config | ✅ Migrated | → `drift_config` |
| `src/drift/` api | ✅ Migrated | → `drift_sdk.api` |
| `src/drift/` session | ✅ Migrated | → `drift_session` |
| `src/drift/` mcp_server | ✅ Migrated | → `drift_mcp` |
| `src/drift/` output | ✅ Migrated | → `drift_output` |
| `packages/drift/` drift_kit | ⚠️ Residual | Active impl; backlogged (spec/010) |
| `packages/drift/` rules/tsjs | ⚠️ Residual | TypeScript rules; backlogged (spec/010) |

**Overall**: 87% complete (2 residual areas tracked in `work_artifacts/vsa_migration_inventory.md`)
