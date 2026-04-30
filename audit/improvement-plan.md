# Harness Engine Improvement Plan

Date: 2026-04-30

## Prioritized Measures

| Priority | Finding | Cause | Change | Impact | Effort | Risk | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0 | H-AUD-001 | Fehlende Dokumentation | Add root [AGENTS.md](../AGENTS.md) as the agent-neutral harness map. | High | Low | Low | Markdown link check and human-readable map review. |
| P0 | H-AUD-002 | Fehlender Guardrail | Add [scripts/check_agent_harness_contract.py](../scripts/check_agent_harness_contract.py) plus [tests/test_agent_harness_contract.py](../tests/test_agent_harness_contract.py). | High | Medium | Low | Targeted pytest and direct script run. |
| P0 | H-AUD-003 | Fehlende Struktur | Add `audit/` and `AGENTS.md` to [.github/repo-root-allowlist](../.github/repo-root-allowlist) and document the purpose in [docs/ROOT_POLICY.md](../docs/ROOT_POLICY.md). | High | Low | Low | `scripts/check_repo_hygiene.py`. |
| P1 | H-AUD-004 | Fehlender Guardrail | Enforce MCP registration/router boundary with HARNESS004/HARNESS005. | Medium | Low | Low | Unit tests and direct harness check. |
| P1 | H-AUD-005 | Fehlende Observability | Create the audit package: state, plan, change log, follow-up. | Medium | Low | Low | Required-path and link checks. |
| P2 | H-AUD-006 | Fehlende Automatisierung | Replace LLM fallback in `ab_harness.py` with a real adapter or explicit unsupported exit. | Medium | Medium | Medium | A/B harness test covering `--mode llm` behavior. |
| P2 | H-AUD-007 | Drift-Risiko | Decide whether internal A/B targets should default to neutral fixtures. | Medium | Low | Medium | CLI/help tests and benchmark report metadata. |
| P1 | H-AUD-008 | Fehlende Karte | Generate and enforce `audit/harness-tool-map.json` (HARNESS006/007). | High | Low | Low | Targeted pytest plus `--write-tool-map` round-trip. |

## Implemented In This Run

1. Root map and golden-principles docs.
2. Required audit package under `audit/`.
3. Agent harness contract checker with remediation-heavy failures.
4. Tests for every new check category.
5. Make/pre-commit integration.

## Implemented 2026-04-30 (delta hardening)

1. AST-based tool ownership map (`audit/harness-tool-map.json`) generated and enforced (HARNESS006/HARNESS007).
2. `scripts/check_agent_harness_contract.py --write-tool-map` to keep map in sync after MCP tool changes.
3. `scripts/ab_harness.py --mode llm` is now an operative error rather than a silent mock fallback.
4. Audit/follow-up updated; FU-001 closed, FU-003 partially closed.

## Deferred

The A/B harness behavior changes are deferred because they affect benchmark
interpretation and need a small decision record or at least a focused test set.
See [follow-up.md](follow-up.md).
