# Harness Engine Follow-Up

Date: 2026-04-30 (last updated 2026-04-30)

## Remaining Gaps

| ID | Gap | Why Not Fully Automated In This Run | Suggested Next Step | Validation |
| --- | --- | --- | --- | --- |
| FU-001 | ~~`scripts/ab_harness.py --mode llm` falls back to mock mode.~~ **CLOSED 2026-04-30**: `--mode llm` now exits operatively with a remediation hint instead of mislabeling mock outcomes. | -- | -- | `python scripts/ab_harness.py --mode llm run` exits 1. |
| FU-002 | A/B mock default is biased. | Changing default benchmark semantics can invalidate existing trend comparisons. | Decide whether `make ab-harness` should pass `--mock-mode neutral` while preserving the script default for compatibility. | Add report metadata asserting `mock_mode` and expected interpretation. |
| FU-003 | ~~MCP tool catalog is broad and still spread across many routers.~~ **PARTIALLY CLOSED 2026-04-30**: `audit/harness-tool-map.json` now canonicalizes tool to router-owner ownership and is enforced by HARNESS006/HARNESS007. Remaining work: surface per-router capability summaries (input/output schemas) for agents. | A capability-schema summary needs careful redaction and is larger than the current invariant. | Generate a `audit/harness-tool-capabilities.json` derived from MCP tool annotations. | Add a test that every entry in the tool map has a matching capability entry. |
| FU-004 | Session trace is in-memory plus queue log, but no compact repro bundle exists for failed agent turns. | Requires schema design for redaction and trace export. | Add `drift_session_trace --format repro-bundle` or a script that captures session summary, trace, changed files, and last nudge/diff. | Add golden JSON fixture tests. |
| FU-005 | Harness docs are link-checked only for the core map/audit set. | Expanding to all docs can produce unrelated churn. | Gradually extend `MARKDOWN_DOCS` or hand off to the existing markdownlint/doc-link tooling. | Add more docs to `MARKDOWN_DOCS` when they become harness-critical. |
| FU-006 | Import-layer enforcement for all `src/drift` modules remains separate from the new harness check. | `.importlinter` already exists and a broad hard gate could surface unrelated legacy violations. | Keep harness-specific MCP boundary checks hard; evaluate hardening `.importlinter` separately. | Run `lint-imports` and record a staged hardening plan. |

## Next-Agent Entry

1. Run `.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .`.
2. Pick one open `FU-*` item above (FU-001 and FU-003 are now closed/partially closed).
3. Write a failing test before behavior changes.
4. Update [change-log.md](change-log.md) with the implemented delta and validation command.
5. Keep [../AGENTS.md](../AGENTS.md) as a map; put detailed rules in focused docs or checks.
6. When adding or removing an `@mcp.tool()`, also run `python scripts/check_agent_harness_contract.py --write-tool-map` so [harness-tool-map.json](harness-tool-map.json) stays in sync.
