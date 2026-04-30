# Harness Engine Audit Change Log

Date: 2026-04-30

## Implemented Changes

| File | Change | Reason | Validation |
| --- | --- | --- | --- |
| [../AGENTS.md](../AGENTS.md) | Added root agent map with harness components, validation commands, and audit links. | Removes entry ambiguity for future agents. | `check_agent_harness_contract.py` required-path and link checks. |
| [../docs/agent-harness-golden-principles.md](../docs/agent-harness-golden-principles.md) | Added machine-near harness rules AH-GP-001 through AH-GP-007. | Converts recurring bad patterns into checkable principles. | Required-path and link checks. |
| [../audit/harness-engine-audit.md](harness-engine-audit.md) | Added current-state map, control flow, findings, and risks. | Creates repo-local evidence for the harness analysis. | Required-path and link checks. |
| [../audit/improvement-plan.md](improvement-plan.md) | Added prioritized improvement plan with impact, effort, risk, and validation. | Lets a next agent continue without reconstructing the audit. | Required-path and link checks. |
| [../audit/follow-up.md](follow-up.md) | Added remaining gaps and next validation hooks. | Makes deferred product/benchmark decisions explicit. | Required-path and link checks. |
| [../scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) | Added mechanical checks for required files, root allowlist, local Markdown links, and MCP boundaries. | Moves harness quality from prompt-only guidance to executable verification. | [../tests/test_agent_harness_contract.py](../tests/test_agent_harness_contract.py). |
| [../tests/test_agent_harness_contract.py](../tests/test_agent_harness_contract.py) | Added contract tests for every new violation type and formatter output. | Prevents silent weakening of the check. | Targeted pytest. |
| [../Makefile](../Makefile) | Added `agent-harness-check` target. | Gives agents one standard command for the harness contract. | Direct target/script run. |
| [../.pre-commit-config.yaml](../.pre-commit-config.yaml) | Added local `agent-harness-contract` hook. | Runs the harness contract before commits. | `pre-commit run --all-files agent-harness-contract`. |
| [../.github/repo-root-allowlist](../.github/repo-root-allowlist) | Added `AGENTS.md` and `audit`. | Keeps root hygiene compatible with the new root map and audit package. | [../scripts/check_repo_hygiene.py](../scripts/check_repo_hygiene.py). |
| [../docs/ROOT_POLICY.md](../docs/ROOT_POLICY.md) | Documented `audit/` as the place for repo-level agent/harness audits. | Avoids a hidden exception to root policy. | Link/read review plus repo hygiene check. |
| [../DEVELOPER.md](../DEVELOPER.md) | Added the harness check to agent workflow command references. | Makes the new check discoverable outside the root map. | Markdown link check via pre-commit markdownlint scope if run. |

## Validation Log

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m drift --version` | `drift, version 2.48.5` |
| `.venv\Scripts\python.exe -m ruff check scripts/check_agent_harness_contract.py tests/test_agent_harness_contract.py` | `All checks passed!` |
| `.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short` | `6 passed in 0.23s` |
| `.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py tests/test_repo_hygiene.py -q --tb=short` | `9 passed in 0.26s` |
| `.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .` | `Agent harness contract: OK` |
| `.venv\Scripts\python.exe scripts\check_repo_hygiene.py` | `OK: Blocklist and root-allowlist checks passed.` |
| `.venv\Scripts\pre-commit.exe run --all-files agent-harness-contract` | `Passed` |
| `make agent-harness-check` | `Agent harness contract: OK` |

## Global Gate Notes

| Command | Result |
| --- | --- |
| `make gate-check COMMIT_TYPE=chore` | Blocked by unrelated active Gate 6 finding for [../src/drift/arch_graph/_skill_writer.py](../src/drift/arch_graph/_skill_writer.py) and Gate 8 requiring full `make check`. |
| `make check PYTHON=.venv\Scripts\python.exe RUFF=".venv\Scripts\python.exe -m ruff" MYPY=".venv\Scripts\python.exe -m mypy" PYTEST=".venv\Scripts\python.exe -m pytest"` | Blocked during lint by unrelated [../tests/conftest.py](../tests/conftest.py) Ruff findings. |

## Design Choice

The implemented changes avoid broad MCP refactoring. The root problem was not
missing low-level session machinery; it was missing harness-level navigation and
mechanical enforcement. The new check is deliberately small and fails with
specific remediation text so future agents can repair the structure without
guessing.

## 2026-04-30 — Tool ownership invariant and operative LLM-mode error

| File | Change | Reason | Validation |
| --- | --- | --- | --- |
| [../scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) | Added AST-based tool-map parser, `check_mcp_tool_router_ownership`, and `--write-tool-map` CLI flag (HARNESS006/HARNESS007). | Made the implicit tool to router mapping a repo-local, agent-readable, mechanically enforced map; added garbage-collection against future inline business logic in the registration shell. | Targeted pytest plus direct script run. |
| [../audit/harness-tool-map.json](harness-tool-map.json) | New canonical map of every `@mcp.tool()` registration to its router-owner module. | Removes the need to read 1900+ lines of `mcp_server.py` to learn which router owns a tool. Drift between source and map fails the contract. | `python scripts/check_agent_harness_contract.py --root .`. |
| [../tests/test_agent_harness_contract.py](../tests/test_agent_harness_contract.py) | Added 5 tests for parser, drift detection, inline-allowlist behavior, and `--write-tool-map`. | Prevents silent weakening of the new invariant. | `pytest tests/test_agent_harness_contract.py -q`. |
| [../scripts/ab_harness.py](../scripts/ab_harness.py) | `--mode llm` now exits with an operative error and remediation hint instead of silently falling back to mock and mislabeling outcomes. | Closes FU-001. Prevents misleading evaluation data. | Direct CLI run with `--mode llm`. |
| [../audit/follow-up.md](follow-up.md) | Closed FU-001; reframed FU-003 as a delta hardening over the new map. | Keeps the deferred backlog honest. | Read review. |

### Validation Log

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .` | `Agent harness contract: OK` |
| `.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --write-tool-map` | `Wrote audit\harness-tool-map.json` (33 tools, 0 inline-only) |
| `.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short` | `11 passed` |
| `.venv\Scripts\python.exe scripts/ab_harness.py --mode llm run` | exit 1 with operative error and FU-001 reference |
