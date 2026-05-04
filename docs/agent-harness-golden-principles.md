# Agent Harness Golden Principles

These rules turn recurring agent-harness failure modes into machine-near
contracts. Prefer checks, tests, structured artifacts, and clear exit signals
over prompt-only reminders.

## Scope

This document covers the Drift agent harness: MCP tools, session orchestration,
agent tasks, evaluation scripts, prompt/skill navigation, and repo-local audit
artifacts. Product policy remains in [../POLICY.md](../POLICY.md) and operative
agent instructions remain in [../.github/copilot-instructions.md](../.github/copilot-instructions.md).

## Rules

| ID | Rule | Enforcement | Remediation |
| --- | --- | --- | --- |
| AH-GP-001 | A new agent must find the harness map from the repo root in one step. | [../scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) requires [../AGENTS.md](../AGENTS.md). | Update the root map or add a reviewed replacement to `REQUIRED_PATHS`. |
| AH-GP-002 | Harness audit work must leave versioned artifacts, not terminal-only findings. | The harness contract check requires the four files under [../audit/](../audit/). | Add or update the audit file that records state, plan, change log, or follow-up. |
| AH-GP-003 | New root entries for harness work must pass root hygiene. | The harness contract check requires `AGENTS.md` and `audit` in [../.github/repo-root-allowlist](../.github/repo-root-allowlist); [../scripts/check_repo_hygiene.py](../scripts/check_repo_hygiene.py) enforces tracked root discipline. | Add the root entry with a documented reason or move the artifact under an existing allowed directory. |
| AH-GP-004 | Agent-facing Markdown must not point to missing local documents. | The harness contract check validates local Markdown links in the harness map and audit docs. | Fix the link or create the referenced artifact. |
| AH-GP-005 | `mcp_server.py` stays a registration shell; MCP business logic belongs in routers/helpers. | The harness contract check blocks top-level business-layer imports in [../src/drift/mcp_server.py](../src/drift/mcp_server.py). | Move logic into `src/drift/mcp_router_*.py`, [../src/drift/mcp_orchestration.py](../src/drift/mcp_orchestration.py), or [../src/drift/mcp_utils.py](../src/drift/mcp_utils.py). |
| AH-GP-006 | MCP router modules must not import the server registration module. | The harness contract check blocks `drift.mcp_server` imports from `src/drift/mcp_router_*.py`. | Move shared code to a neutral helper module to keep registration and routing acyclic. |
| AH-GP-007 | Evaluation output must say whether it measures agent behavior or fixture bias. | Current status is documented in [../audit/follow-up.md](../audit/follow-up.md). | Prefer neutral fixtures by default or record why a biased fixture is intentionally used. |
| AH-GP-008 | Repo-level A/B harness automation must default to neutral mock fixtures. | The harness contract check blocks `make ab-harness` unless the run step passes `--mock-mode neutral`; [../scripts/ab_harness.py](../scripts/ab_harness.py) records `mock_mode` and `mock_mode_interpretation` in reports. | Use `--mock-mode neutral` for the Make target; use biased mode only as an explicit compatibility run. |
| AH-GP-009 | Context-engineering work must separate static and dynamic context and keep the contract discoverable from the harness entry surfaces. | The harness contract check requires a dedicated [../.github/prompts/drift-context-engineering.prompt.md](../.github/prompts/drift-context-engineering.prompt.md), the shared [../.github/prompts/_partials/context-engineering-contract.md](../.github/prompts/_partials/context-engineering-contract.md), a prompt-catalog entry, and harness-engine wiring. | Keep context rules repo-local, reference the shared contract instead of duplicating lists, and route stale-context diagnosis through the dedicated prompt before follow-up implementation. |
| AH-GP-010 | Architecture guidance in harness follow-ups must become mechanical layer constraints, not style advice. | The harness contract check requires [../.github/prompts/drift-harness-followup.prompt.md](../.github/prompts/drift-harness-followup.prompt.md) to name the `Types -> Config -> Repo -> Service -> Runtime -> UI` chain, the leftward import rule, and enforcement surfaces such as structure tests, pre-commit, CI, deterministic linters, or LLM auditors. | Encode missing architecture intent as a test, contract check, script, or machine-readable rule before adding more prose. |

## Required Check

Run this before claiming an agent-harness change is complete:

```powershell
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
```

For regression coverage, run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
```
