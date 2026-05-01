# Drift Agent Root Map

This file is the agent-neutral entry map for the Drift repository. It is a
map, not a rulebook: follow the linked source files for the operative rules.

## Start Here

1. Read the mandatory agent rules in [.github/copilot-instructions.md](.github/copilot-instructions.md).
2. Run the policy gate from [.github/instructions/drift-policy.instructions.md](.github/instructions/drift-policy.instructions.md) before file work.
3. Use [DEVELOPER.md](DEVELOPER.md) for setup, commands, architecture overview, and targeted tests.
4. Use [.github/AGENTS.md](.github/AGENTS.md) for the prompt, skill, and evaluation-prompt catalogue.

## Harness Engine Map

The harness is distributed across MCP tools, session state, benchmarks, and
agent-facing docs:

| Area | Primary artifacts | Contract |
| --- | --- | --- |
| MCP entrypoint | [src/drift/mcp_server.py](src/drift/mcp_server.py), [.vscode/mcp.json](.vscode/mcp.json) | Register tools and delegate business logic to router modules. |
| Session loop | [src/drift/session.py](src/drift/session.py), [src/drift/mcp_orchestration.py](src/drift/mcp_orchestration.py), [src/drift/mcp_router_session.py](src/drift/mcp_router_session.py) | Preserve state, trace, queue replay, guardrails, and handover gates across turns. |
| Agent tasks | [src/drift/models/_agent.py](src/drift/models/_agent.py), [src/drift/output/agent_tasks.py](src/drift/output/agent_tasks.py) | Emit machine-readable repair tasks with constraints and verification plans. |
| Evaluation harness | [scripts/ab_harness.py](scripts/ab_harness.py), [scripts/benchmark_agent_loop.py](scripts/benchmark_agent_loop.py), [scripts/run_agent_loop_benchmark.py](scripts/run_agent_loop_benchmark.py) | Measure agent loop efficiency, severity-gate routing, and brief effectiveness. |
| Mechanical harness check | [scripts/check_agent_harness_contract.py](scripts/check_agent_harness_contract.py), [tests/test_agent_harness_contract.py](tests/test_agent_harness_contract.py) | Verify required docs, audit artifacts, root allowlist entries, Markdown links, and MCP boundaries. |

## Golden Principles

Machine-near harness rules live in [docs/agent-harness-golden-principles.md](docs/agent-harness-golden-principles.md). Add or tighten a mechanical check whenever a rule can be verified by code, tests, or CI.

## Audit Trail

The current harness audit deliverables are versioned under [audit/](audit/):

- [audit/harness-engine-audit.md](audit/harness-engine-audit.md) - current-state map and risks
- [audit/improvement-plan.md](audit/improvement-plan.md) - prioritized backlog and validation method
- [audit/change-log.md](audit/change-log.md) - implemented changes and checks
- [audit/follow-up.md](audit/follow-up.md) - gaps that still need design or automation
- [audit/harness-tool-map.json](audit/harness-tool-map.json) - canonical MCP tool to router-owner map (HARNESS006/007)

## Validation Commands

Use these commands for local agent-harness changes:

```powershell
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
make agent-harness-check
```

For source-file-specific checks, use the map in [DEVELOPER.md](DEVELOPER.md#quelldatei--empfohlene-tests-agents--fix-loop) or run:

```powershell
make test-for FILE=src/drift/session.py
```
