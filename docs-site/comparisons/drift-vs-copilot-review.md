# Drift vs GitHub Copilot Code Review

GitHub Copilot Code Review (GA since March 2026) and drift operate at different
positions in the developer workflow. They address different questions at different
times.

## Short answer

Copilot Code Review checks code after it is written — it reviews pull requests.
Drift operates before and during: `drift brief` generates guardrails
**before** an agent task starts, `drift nudge` checks direction **during** the
editing session.

These are not competing tools. They are complementary stages in the same workflow.

## Where each tool sits in the workflow

```
[drift brief]       → pre-task guardrails (before writing any code)
[drift nudge]       → inner-loop feedback (while editing, via MCP)
─────────────────── code is written ──────────────────────────────
[Copilot Review]    → PR review (after code is complete)
[drift analyze]     → full repo health assessment (periodic / CI gate)
```

Copilot Code Review improves the **post-task verification** stage. Drift
improves the **pre-task prevention** stage and the **in-session feedback** stage.

## Comparison

| Capability | Drift | Copilot Code Review |
|---|:---:|:---:|
| Pre-task architectural guardrails | **Yes** (`drift brief`) | No |
| Inner-loop directional feedback | **Yes** (`drift nudge` via MCP) | No |
| Post-PR code review | No | **Yes** |
| Deterministic findings | **Yes** | No (LLM-based) |
| SARIF output for GitHub Code Scanning | **Yes** | Partial (CodeQL findings) |
| Trend tracking over time | **Yes** (`drift trend`) | No |
| Temporal signals (TVS, CCC) | **Yes** | No |
| Bayesian per-repo calibration | **Yes** | No |
| Requires Copilot subscription | No | Yes |
| Zero server setup | **Yes** | N/A (cloud) |
| CI gate with exit codes | **Yes** | No |

## What `drift brief` does that Copilot Review cannot

When an agent receives a task description like "add payment integration",
`drift brief` analyzes the affected scope **before any code is generated** and
returns:

- Which signals are elevated in the files the task will touch
- Concrete guardrails (prompt constraints) the agent should follow
- A risk level (LOW / MEDIUM / HIGH / BLOCK) for the planned change

This is structural context that influences how the agent writes the code,
not a review of code that has already been generated.

Copilot Code Review cannot provide this because it requires finished code to
review. The prevention window — the moment before an agent makes structural
choices — is drift's exclusive operating position.

## What Copilot Review does that drift does not

Copilot Code Review is strong at:

- Line-by-line code quality feedback in the PR diff
- Identifying logic issues, edge cases, and naming problems in new code
- CodeQL-backed security finding integration
- Inline PR comments and conversation threading

These are post-hoc review capabilities. Drift does not aim to replace them.

## Recommended combined workflow

1. `drift brief --task "..."` — before starting the agent session, get guardrails
2. Agent writes code, `drift nudge` runs via MCP after each file edit
3. `git push` → PR opens → Copilot Code Review runs
4. `drift analyze` in CI as a weekly or per-release health gate

## Where to go next

- [MCP & AI Tools Integration](../integrations.md)
- [Pre-task Guardrails: drift brief](../getting-started/prompts.md)
- [CI Architecture Checks with SARIF](../use-cases/ci-architecture-checks-sarif.md)
- [Case Studies](../case-studies/index.md)
