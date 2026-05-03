# Agent Harness Golden Principles

## What is Harness Engineering?

### The Horse Metaphor

The term *harness* comes from equestrian sport — reins, saddle, bit: the
complete equipment to steer a powerful but unpredictable animal in the right
direction. The metaphor is deliberate:

- **The horse** is the AI model — powerful, fast, but with no innate sense of
  where to go.
- **The harness** is the infrastructure — constraints, guardrails, feedback
  loops that channel the model's power productively.
- **The rider** is the human engineer — setting direction without running
  themselves.

Without a harness, an AI agent is like a thoroughbred in an open field: fast,
impressive — and completely useless for getting anything done.

### Formal Definition

Harness engineering is the design and implementation of systems that channel
an AI agent's capabilities productively. It rests on three pillars:

**1. Context Engineering** — Ensure the agent has the right information at the
right time.

*Static context:*
- Repository-local documentation (architecture specs, API contracts, style guides)
- `AGENTS.md` / `CLAUDE.md` files encoding project-specific rules
- Cross-linked design documents validated by linters

*Dynamic context:*
- Observability data (logs, metrics, traces) the agent can access
- Directory structure mappings generated at agent startup
- CI/CD pipeline status and test results

The critical rule: **from the agent's perspective, nothing exists that it cannot
access in context.** Knowledge in Google Docs, Slack threads, or people's heads
is invisible to the system. The repository must be the single source of truth.

**2. Architectural Constraints** — This is where harness engineering differs
most sharply from traditional AI prompting. Instead of telling the agent "write
good code", you mechanically enforce what good code looks like.

*Dependency layers:*

```
Types → Config → Repo → Service → Runtime → UI
```

Each layer may only import from layers to its left. This is not a suggestion —
it is enforced by structure tests and CI validation.

*Enforcement tools:*
- **Deterministic linters** — custom rules that flag violations automatically
- **LLM-based auditors** — agents that review other agents' code for
  architectural conformance
- **Structure tests** — like ArchUnit, but for AI-generated code
- **Pre-commit hooks** — automated checks before code is committed

Why constraints improve outcomes: paradoxically, restricting the solution space
makes agents *more* productive. When an agent can generate anything, it wastes
tokens exploring dead ends. When the harness defines clear boundaries, the agent
converges on correct solutions faster.

**3. Entropy Management ("Garbage Collection")** — This is the most
underestimated component. Over time, AI-generated codebases accumulate entropy:
documentation drifts from reality, naming conventions diverge, dead code
accumulates.

Harness engineering addresses this with periodic cleanup agents:

- **Documentation consistency agents** — verify that documents match the
  current code
- **Constraint violation scans** — find code that slipped through earlier checks
- **Pattern enforcement agents** — identify and fix deviations from established
  patterns
- **Dependency auditors** — track and resolve circular or unnecessary
  dependencies

These agents run on a schedule — daily, weekly, or triggered by specific events
— and keep the codebase healthy for both human reviewers and future AI agents.

A good harness makes agents **more capable**, not just more controlled.

### The Three Pillars in Drift

| Pillar | Drift Implementation |
| --- | --- |
| Context Engineering | `AGENTS.md`, `work_artifacts/index.json`, session handover, `drift_retrieve`, `drift_cite` |
| Architectural Constraints | `check_agent_harness_contract.py`, layer import rules, pre-commit, CI, `drift_nudge` gate |
| Entropy Management | `make update-artifacts-index`, `make handover`, `work_artifacts/` folder structure, `blast_reports/` naming schema |

---

## Common Mistakes in Harness Engineering

### 1. Over-Engineering the Control Flow

> "If you over-engineer the control flow, the next model update will destroy your system."

Models improve rapidly. Capabilities that required complex pipelines in 2024 are
handled today by a single prompt in the context window. Build your harness to be
modular and *rippable* — you should be able to remove "smart" logic when the
model becomes capable enough to no longer need it.

### 2. Treating the Harness as Static

The harness must evolve with the model. When a new model release improves
reasoning, your middleware for reasoning optimization may become
counterproductive. Review and update harness components with every major model
update.

### 3. Ignoring the Documentation Layer

The most impactful harness improvement is often the simplest: better
documentation. If your `AGENTS.md` is vague, your agent's output will be vague.
Invest in precise, machine-readable documentation that serves as ground truth
for the agent.

### 4. Missing Feedback Loops

A harness without feedback is a cage, not a guide. The agent must know when it
succeeds and when it fails. Build in:

- Self-verification steps before completing a task
- Test execution as part of the agent workflow
- Metrics on agent success rates by task type

### 5. Documentation That Lives Outside the Repository

If your architectural decisions live in people's heads or on Confluence pages
the agent cannot access, the harness has a gap. Everything the agent needs must
live in the repository.

---

## Agents SDK Orientation

Sandbox agents are available in the Python Agents SDK. Use them when your
agent needs a container-based environment with files, commands, packages,
ports, snapshots, and memory.

- Sandbox agents guide: [https://developers.openai.com/api/docs/guides/agents/sandboxes](https://developers.openai.com/api/docs/guides/agents/sandboxes)

Agents are applications that plan, call tools, collaborate across specialists,
and keep enough state to complete multi-step work.

- Use OpenAI client libraries when you want direct API clients for model requests.
- Use Agents SDK guides when your application owns orchestration, tool execution, approvals, and state.
- Use Agent Builder only when you specifically want the hosted workflow editor and ChatKit path.

### Get the Agents SDK

- TypeScript SDK repository: [https://github.com/openai/openai-agents-js](https://github.com/openai/openai-agents-js)
- Python SDK repository: [https://github.com/openai/openai-agents-python](https://github.com/openai/openai-agents-python)

### Choose Your Starting Point

| If you want to | Start here | Why |
| --- | --- | --- |
| Build a code-first agent app | [Quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart) | Shortest path to a working SDK integration. |
| Define one specialist cleanly | [Agent definitions](https://developers.openai.com/api/docs/guides/agents/define-agents) | Start here when shaping one agent contract. |
| Choose models, defaults, and transport | [Models and providers](https://developers.openai.com/api/docs/guides/agents/models) | Use when model choice or provider setup impacts workflow. |
| Understand the runtime loop and state | [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents) | Covers loop behavior, streaming, and continuation. |
| Run work in a container environment | [Sandbox agents](https://developers.openai.com/api/docs/guides/agents/sandboxes) | Use for files, commands, packages, snapshots, mounts, and provider links. |
| Design specialist ownership | [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration) | Use when multiple agents need clear ownership of replies. |
| Add validation or human review | [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals) | Use when workflow must pause before risky work continues. |
| Understand what a run returns | [Results and state](https://developers.openai.com/api/docs/guides/agents/results) | Explains final output and resumable state. |
| Add hosted tools, function tools, or MCP | [Using tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk) and [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability) | Tools semantics live in platform docs; SDK-specific MCP/tracing live in integrations docs. |
| Inspect and improve runs | [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability) and [Evaluate agent workflows](https://developers.openai.com/api/docs/guides/agent-evals) | Start with traces, then evaluation loops. |
| Build a voice-first workflow | [Voice agents](https://developers.openai.com/api/docs/guides/voice-agents) | Voice is currently an SDK-first path. |

### Build with the SDK

Use the SDK track when your server owns orchestration, tool execution, state,
and approvals. This path fits best when you need:

- typed application code in TypeScript or Python
- direct control over tools, MCP servers, and runtime behavior
- custom storage or server-managed conversation strategies
- tight integration with existing product logic or infrastructure

Typical reading order:

1. [Quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart)
2. [Agent definitions](https://developers.openai.com/api/docs/guides/agents/define-agents) and [Models and providers](https://developers.openai.com/api/docs/guides/agents/models)
3. [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents), [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration), [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
4. [Results and state](https://developers.openai.com/api/docs/guides/agents/results) and [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)

### Quickstart

Use this when you want the shortest path to a working **GitHub Copilot Pro+**
workflow with **no OpenAI or third-party API key**. The examples below are
local, runnable patterns that mirror agent behavior (specialists, tools,
handoffs) without calling external model APIs.

#### Setup (Copilot Pro+, no API key)

1. Install the VS Code extension `GitHub.copilot-chat`.
2. Sign in with your GitHub account that has Copilot Pro+.
3. Open this repository in VS Code.
4. Use Copilot Chat/Agent mode for planning, edits, and verification.

```bash
# Optional local runtimes for examples below (no API key required)
npm install -D tsx typescript
pip install rich
```

#### Create and run your first local "agent" loop

Start with one focused specialist and one turn in local code. This gives a
real execution path that works in any Copilot Pro+ workspace without API keys.

```typescript
type Specialist = (question: string) => string;

const historyTutor: Specialist = (question) => {
  if (question.toLowerCase().includes("roman empire")) {
    return "The Western Roman Empire is commonly dated to 476 CE.";
  }
  return "I can answer history questions clearly and concisely.";
};

const answer = historyTutor("When did the Roman Empire fall?");
console.log(answer);
```

```python
from typing import Callable

Specialist = Callable[[str], str]


def history_tutor(question: str) -> str:
    if "roman empire" in question.lower():
        return "The Western Roman Empire is commonly dated to 476 CE."
    return "I can answer history questions clearly and concisely."


print(history_tutor("When did the Roman Empire fall?"))
```

Once this loop works, keep the same shape and add capabilities incrementally
instead of starting with a large multi-agent design.

#### Carry state into the next turn

| If you want | Start with |
| --- | --- |
| Keep full history in your app | A local `history` list persisted by your app |
| Reuse session state in Copilot tasks | `work_artifacts/session_*.md` handover files |
| Resume after interruption | Last saved handover + pending task list |
| Keep specialist ownership across turns | Store `active_specialist` in local state |

After handoffs, reuse your saved state for the next turn when the same
specialist should remain in control.

#### Give the workflow a tool

The first capability you add is often a local function tool.

```typescript
const historyFunFact = () => "Sharks are older than trees.";

function historyTutor(question: string): string {
  if (question.toLowerCase().includes("surprising")) {
    return historyFunFact();
  }
  return "Ask me for a surprising history fact.";
}

console.log(historyTutor("Tell me something surprising about ancient life on Earth."));
```

```python
def history_fun_fact() -> str:
    return "Sharks are older than trees."


def history_tutor(question: str) -> str:
    if "surprising" in question.lower():
        return history_fun_fact()
    return "Ask me for a surprising history fact."


print(history_tutor("Tell me something surprising about ancient life on Earth."))
```

Use [Using tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)
for hosted tool semantics when you move from local keyless prototypes to SDK
server runtimes.

#### Add specialist agents

A common next step is splitting workflows into specialists and routing with
handoffs.

```typescript
function historyTutor(question: string): string {
  return "George Washington was the first U.S. president.";
}

function mathTutor(question: string): string {
  return "Let's solve it step by step.";
}

function triage(question: string): { specialist: string; answer: string } {
  const q = question.toLowerCase();
  if (q.includes("president") || q.includes("history")) {
    return { specialist: "history", answer: historyTutor(question) };
  }
  return { specialist: "math", answer: mathTutor(question) };
}

const result = triage("Who was the first president of the United States?");
console.log(result.answer);
console.log(result.specialist);
```

```python
def history_tutor(question: str) -> str:
    return "George Washington was the first U.S. president."


def math_tutor(question: str) -> str:
    return "Let's solve it step by step."


def triage(question: str) -> tuple[str, str]:
    q = question.lower()
    if "president" in q or "history" in q:
        return history_tutor(question), "history"
    return math_tutor(question), "math"


answer, specialist = triage("Who was the first president of the United States?")
print(answer)
print(specialist)
```

#### Inspect traces early

In Copilot Pro+ workflows, inspect execution evidence early:

- terminal output from your local examples
- changed files and diffs
- test/lint output from the repo workflow

When you later move to SDK server runtimes, use the
[Traces dashboard](https://platform.openai.com/traces) to inspect model calls,
tool calls, handoffs, and guardrails.

#### Next steps

- [Agent definitions](https://developers.openai.com/api/docs/guides/agents/define-agents) for shaping one specialist cleanly
- [Using tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk) for hosted tools, function tools, and agents-as-tools
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents) for loop, streaming, and continuation strategies
- [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration) for multi-specialist ownership rules

### Agent Builder for Hosted Workflows

Use Agent Builder when you want OpenAI-hosted workflow creation, publishing,
and ChatKit deployment.

Voice agents are the exception: they remain in the SDK track because Agent
Builder does not currently support voice workflows.

---

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

## Required Check

Run this before claiming an agent-harness change is complete:

```powershell
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
```

For regression coverage, run:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
```
