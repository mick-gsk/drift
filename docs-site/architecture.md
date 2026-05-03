# Architecture Overview — Drift Monorepo

> For contributors and integrators who need to understand how Drift's packages relate.

---

## Package Quick-Reference

| Package | Install name | Purpose | Key entry points |
|---|---|---|---|
| `packages/drift-engine` | `drift-engine` | Analysis engine: signals, scoring, pipeline, ingestion | `drift_engine.pipeline`, `drift_engine.signals` |
| `packages/drift-cli` | `drift-cli` | Click CLI commands | `drift_cli.cli`, `drift_cli.commands.*` |
| `packages/drift-config` | `drift-config` | Config schema, profile detection, path overrides | `drift_config`, `drift_config.detect_repo_profile` |
| `packages/drift-sdk` | `drift-sdk` | Public Python SDK, MCP tool API | `drift_sdk.api`, `drift_sdk.api.scan` |
| `packages/drift-session` | `drift-session` | Session state, outcome tracking, reward chain | `drift_session.session.DriftSession` |
| `packages/drift-mcp` | `drift-mcp` | MCP server (FastMCP), router dispatch | `drift_mcp.mcp_server` |
| `packages/drift-output` | `drift-output` | Rich terminal, JSON, SARIF output renderers | `drift_output.rich_output`, `drift_output.json_output` |
| `packages/drift-verify` | `drift-verify` | Verification pipeline | `drift_verify` |
| `packages/drift` | `drift-analyzer` | Compat meta-package: re-exports all above | `drift.*` (public API) |

---

## Import Hierarchy

```
External user code / tests
        │  from drift.signals import X
        ▼
  packages/drift/src/drift/        ← compat layer (re-exports, read-only)
  e.g. drift.signals → sys.modules alias
        │
        ▼
  packages/drift-engine/src/drift_engine/signals/   ← canonical implementation
```

**Leftward-only rule**: Lower-layer packages (engine, config) must not import from higher-level packages (cli, mcp, output). Information flows upward.

---

## Capability Ownership by Slice

```
CLI user input
      │ drift_cli.commands.*
      ▼
MCP tool calls
      │ drift_mcp.mcp_server.*
      ▼
Public SDK / API
      │ drift_sdk.api.*
      ▼
Analysis Engine
      │ drift_engine.pipeline
      │ drift_engine.signals.*
      │ drift_engine.scoring
      ▼
Configuration
      │ drift_config
      ▼
Output
      │ drift_output.rich_output / json_output / sarif
```

---

## Verification

```bash
# Verify no active implementation leaked into compat layer
python scripts/migration/audit_legacy_paths.py

# Verify no import boundary violations
python scripts/migration/check_import_boundaries.py

# Full boundary test suite
pytest tests/migration/ -v
```

For the complete architecture document with boundary rules see [docs/architecture/vsa-monorepo.md](../../docs/architecture/vsa-monorepo.md).
