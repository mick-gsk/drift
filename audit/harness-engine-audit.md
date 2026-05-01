# Harness Engine Audit

Date: 2026-04-30
Repository: `mick-gsk/drift`
Validated dev version: `drift, version 2.48.5`

## Scope

This audit covers the repo-local agent harness: MCP tool surface, session and
turn state, task contracts, skills/prompts, validation scripts, and agent-facing
navigation. It does not re-audit signal precision or product scoring.

## 1. Ist-Zustand

### Entry Points

- [AGENTS.md](../AGENTS.md) is now the root map for agent entry.
- [.github/copilot-instructions.md](../.github/copilot-instructions.md) is the mandatory workspace instruction set for Copilot agents.
- [.github/AGENTS.md](../.github/AGENTS.md) lists release/evaluation prompts and core skills.
- [DEVELOPER.md](../DEVELOPER.md) provides setup, architecture overview, command map, and targeted tests.
- [.vscode/mcp.json](../.vscode/mcp.json) wires the `drift` and `drift-repo-ops` MCP servers to `.venv`.

### Control Flow

1. MCP clients start [src/drift/mcp_server.py](../src/drift/mcp_server.py), which registers tools such as `drift_scan`, `drift_diff`, `drift_fix_plan`, `drift_nudge`, `drift_session_start`, `drift_session_end`, `drift_retrieve`, and `drift_cite`.
2. Tool bodies delegate to router modules such as [src/drift/mcp_router_analysis.py](../src/drift/mcp_router_analysis.py), [src/drift/mcp_router_repair.py](../src/drift/mcp_router_repair.py), and [src/drift/mcp_router_session.py](../src/drift/mcp_router_session.py).
3. [src/drift/session.py](../src/drift/session.py) owns multi-turn state: session TTL, phase, trace, selected tasks, completed tasks, active leases, diagnostics, timing metrics, and handover retries.
4. [src/drift/mcp_orchestration.py](../src/drift/mcp_orchestration.py) resolves session defaults, advances phases, emits semantic pre-call advisories, enforces strict guardrails, validates diagnostic hypotheses, and records verification outcomes.
5. [src/drift/mcp_router_session.py](../src/drift/mcp_router_session.py) creates/resumes sessions, replays queue logs, detects concurrent writers, routes stale plans back to `drift_fix_plan`, and routes fresh pending queues to `drift_fix_apply`.
6. Agent tasks are modeled in [src/drift/models/_agent.py](../src/drift/models/_agent.py) and exported via [src/drift/output/agent_tasks.py](../src/drift/output/agent_tasks.py).

### Evaluation And Observability

- [scripts/benchmark_agent_loop.py](../scripts/benchmark_agent_loop.py) measures scan/nudge/fix-plan/context-export API calls and timings.
- [scripts/run_agent_loop_benchmark.py](../scripts/run_agent_loop_benchmark.py) validates AUTO/REVIEW/BLOCK severity routing and schema-2.2 telemetry output.
- [scripts/ab_harness.py](../scripts/ab_harness.py) runs paired control/treatment A/B tasks and writes outcomes/stats/report under `work_artifacts/internal_eval/ab_harness`.
- [tests/test_agent_loop_benchmark.py](../tests/test_agent_loop_benchmark.py), [tests/test_agent_telemetry_schema.py](../tests/test_agent_telemetry_schema.py), and [tests/test_session_end_gate.py](../tests/test_session_end_gate.py) cover core benchmark, telemetry, and handover contracts.

### Validation And Gates

- [Makefile](../Makefile) exposes `feat-start`, `fix-start`, `gate-check`, `audit-diff`, `handover`, and now `agent-harness-check`.
- [.pre-commit-config.yaml](../.pre-commit-config.yaml) runs hygiene/security checks and now includes the agent harness contract check.
- [scripts/check_repo_hygiene.py](../scripts/check_repo_hygiene.py) enforces root allowlist discipline from [.github/repo-root-allowlist](../.github/repo-root-allowlist).
- [scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) now checks harness docs, audit artifacts, Markdown links, root allowlist entries, and MCP boundary imports.

## 2. Befunde

| ID | Severity | Ursache | Auswirkung | Belegstelle | Status |
| --- | --- | --- | --- | --- | --- |
| H-AUD-001 | High | Fehlende Dokumentation | Agents had to infer the harness map from scattered files instead of starting from a root-neutral map. | [.github/AGENTS.md](../.github/AGENTS.md), [DEVELOPER.md](../DEVELOPER.md), missing root `AGENTS.md` before this change | Fixed by [AGENTS.md](../AGENTS.md). |
| H-AUD-002 | High | Fehlender Guardrail | Harness docs and audit deliverables were not mechanically required, so future agents could skip them without a local failure. | New RED output from `scripts/check_agent_harness_contract.py --root .` reported missing required artifacts. | Fixed by [scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) and [tests/test_agent_harness_contract.py](../tests/test_agent_harness_contract.py). |
| H-AUD-003 | Medium | Fehlende Struktur | User-requested root `audit/` artifacts would violate existing root hygiene unless allowlisted and documented. | [docs/ROOT_POLICY.md](../docs/ROOT_POLICY.md), [.github/repo-root-allowlist](../.github/repo-root-allowlist), [scripts/check_repo_hygiene.py](../scripts/check_repo_hygiene.py) | Fixed by updating root policy and allowlist. |
| H-AUD-004 | Medium | Fehlender Guardrail | MCP server/router separation was documented in code comments but not checked as a harness boundary. | [src/drift/mcp_server.py](../src/drift/mcp_server.py), [src/drift/mcp_orchestration.py](../src/drift/mcp_orchestration.py) | Fixed by HARNESS004/HARNESS005 checks. |
| H-AUD-005 | Medium | Fehlende Observability | Harness improvement work had no standard audit package tying state, plan, change log, and follow-up together. | No `audit/` directory before this change. | Fixed by this audit package. |
| H-AUD-006 | Low | Fehlende Automatisierung | [scripts/ab_harness.py](../scripts/ab_harness.py) exposes `--mode llm` but currently falls back to mock mode for LLM runs. | [scripts/ab_harness.py](../scripts/ab_harness.py) | Fixed 2026-04-30: `--mode llm` now exits operatively; closed FU-001. |
| H-AUD-007 | Low | Drift-Risiko | The default A/B mock mode is biased and its own help text says it can measure structural bias rather than brief effectiveness. | [scripts/ab_harness.py](../scripts/ab_harness.py) | Documented in [follow-up.md](follow-up.md) as FU-002. |
| H-AUD-008 | Medium | Fehlende Karte | Tool to router-owner mapping was implicit across 1900+ lines of `mcp_server.py`; agents had no machine-readable catalog and no enforcement against new inline business logic. | [src/drift/mcp_server.py](../src/drift/mcp_server.py), missing `audit/harness-tool-map.json` before this change | Fixed 2026-04-30 by HARNESS006/HARNESS007 in [scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) and [audit/harness-tool-map.json](harness-tool-map.json). |

## 3. Risk Summary

The highest leverage fixes were not broad MCP rewrites. The critical gaps were
entry clarity and enforcement: agents need to find the harness quickly, and the
repo needs to fail early when that map, audit package, links, or MCP boundaries
drift.

## 4. Validation Paths

- `.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short`
- `.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .`
- `.venv\Scripts\python.exe scripts\check_repo_hygiene.py`
- `.venv\Scripts\python.exe -m drift --version`

Detailed validation results are recorded in [change-log.md](change-log.md).
