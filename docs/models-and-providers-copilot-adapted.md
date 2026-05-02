# Models and Providers — GitHub Copilot Pro+ Adapted

This page adapts the [OpenAI Agents SDK Models and Providers guide](https://developers.openai.com/api/docs/guides/agents/models) for **GitHub Copilot Pro+** hosted environments.

## ⚠️ Critical: Model Selection in Copilot Pro+

In **GitHub Copilot Pro+**, the model is **NOT** your choice. The host (GitHub Copilot runtime) selects and injects the model at runtime.

| Decision | Direct SDK (OPENAI_API_KEY) | GitHub Copilot Pro+ |
|----------|----------------------------|---------------------|
| Set `model` on agent | ✓ Yes, explicitly | ✗ No—host injects |
| Set `model` on Runner | ✓ Yes, as default | ✗ No—ignored |
| Set `OPENAI_DEFAULT_MODEL` env var | ✓ Yes, as fallback | ✗ No—host provides |
| **What you actually get** | The model YOU specified | The model GitHub selected for your subscription tier |

**If you try to hardcode a model in Copilot Pro+:**

```python
# ❌ DON'T DO THIS in Copilot Pro+
agent = Agent(
    name="My agent",
    model="gpt-5.5",  # ← Host will override this; your choice has no effect
)
```

The host doesn't error — it silently replaces your choice. Your agent will run, but with the host's model, not yours.

## What You Can Control in Copilot Pro+

| Aspect | Can You Control? | How |
|--------|------------------|-----|
| Instructions | ✓ Yes | Static `instructions` string on each agent |
| Tools and capabilities | ✓ Yes | `tools` array on each agent |
| Structured output format | ✓ Yes | `output_type` on agent |
| Local context (user data, secrets) | ✓ Yes | Pass via run `context` (not sent to model) |
| Prompt template | ✓ Yes | Static `prompt` configuration (if used) |
| **Model selection** | ✗ No | Host controls based on subscription tier |
| **Transport / provider** | ✗ No | Host provides OpenAI transport |
| **Feature flags and tuning** | ⚠️ Partial | Depends on host-provided model capabilities |

## What Model Do You Get?

The model your agents run on depends on your **GitHub Copilot subscription tier**:

| Tier | Model(s) Provided | Latency | Cost |
|------|------------------|--------|------|
| Copilot Pro | gpt-4o or latest available | Standard | Included in subscription |
| Copilot Pro Team | gpt-4o or latest available | Standard | Included in team subscription |
| Free trial | Limited model access | Variable | Time-limited |

You don't select this—it's determined by your subscription. If you need a different model tier, upgrade your subscription tier, not your code.

## How to Think About Agent Definitions in Copilot Pro+

Since the model is host-controlled, your agent definitions should focus on **what the agent is supposed to do**, not **how good the model is**.

### Good Practice: Describe the Specialist's Role

```python
# ✓ GOOD: Describes what the agent does and constraints
agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text. Be precise with dates.",
    tools=[get_calendar_api],
    output_type=CalendarEvent,
    # Model: host-provided, no hardcoding
)
```

### Anti-Pattern: Trying to Control Model Behavior

```python
# ✗ BAD: Trying to control model via instructions
agent = Agent(
    name="Calendar extractor",
    instructions="""Extract calendar events. Use gpt-5.5 for accuracy.
Be very fast; this is latency-critical.""",
    # ↑ Can't control model in instructions; host decides.
)
```

The host controls latency and model capability. Write instructions that describe the **task**, not the **model**.

## Comparing Direct SDK vs. Copilot Pro+

### Example: Multi-Agent Workflow (Direct SDK)

```typescript
// Direct SDK: YOU choose models per specialist
import { Agent, Runner } from "@openai/agents";

const fastTriage = new Agent({
  name: "Fast triage",
  model: "gpt-5.4-mini",  // ← You choose: small model, low cost
  instructions: "Categorize the request.",
});

const deepInvestigator = new Agent({
  name: "Deep investigator",
  model: "gpt-5.5",  // ← You choose: large model, higher quality
  instructions: "Investigate thoroughly.",
});

const runner = new Runner({ model: "gpt-5.5" }); // ← Default for unlabeled agents
await runner.run(fastTriage, "Categorize: 'billing issue'");
```

### Example: Multi-Agent Workflow (Copilot Pro+)

```python
# Copilot Pro+: HOST chooses model; you describe responsibility
import asyncio
from agents import Agent, Runner

fast_triage = Agent(
    name="Fast triage",
    instructions="Categorize the request quickly. Keep response concise.",
    # ✓ No model; host provides
    # ✓ Instructions hint at speed (host adapts if possible)
)

deep_investigator = Agent(
    name="Deep investigator",
    instructions="Investigate thoroughly. Be comprehensive and precise.",
    # ✓ No model; host provides
    # ✓ Instructions hint at thoroughness (host adapts if possible)
)

# Note: Runner model setting is ignored in Copilot Pro+
runner = Runner()  # ← Host handles transport; model is given

async def main():
    await runner.run(fast_triage, "Categorize: 'billing issue'")
    result = await runner.run(deep_investigator, "Investigate: account 456")
    print(result.final_output)
```

**The key difference**: In Direct SDK, you *choose* `gpt-5.4-mini` vs. `gpt-5.5`. In Copilot Pro+, you *describe* the task (`"quickly"` vs. `"thoroughly"`), and the host decides which model it has available.

## When Model Choices Mattered (Pre-Copilot-Pro+)

If you're reading existing Agents SDK code or documentation that shows model selection, those examples assume:

1. You have an OpenAI API key in your environment
2. You have access to multiple model tiers (mini, standard, reasoning variants)
3. You're making cost/latency tradeoffs
4. You're responsible for rate limiting and quota management

**None of those apply in Copilot Pro+.** The host manages all of it.

## Adapting Existing Agents for Copilot Pro+

If you have agents built for Direct SDK (with hardcoded models), adapt them like this:

### Before (Direct SDK)

```python
agent = Agent(
    name="Support specialist",
    instructions="Help the user.",
    model="gpt-5.5",  # ← Hardcoded
)
```

### After (Copilot Pro+)

```python
agent = Agent(
    name="Support specialist",
    instructions="Help the user.",
    # Remove model: host provides
)
```

### What to Remove

- ✓ Remove `model: "gpt-..."` from agent definitions
- ✓ Remove `model: "..."` from Runner configurations
- ✓ Remove `OPENAI_DEFAULT_MODEL` environment variable setup
- ✓ Remove model-selection logic from agent initialization code

### What to Keep

- ✓ Keep all `instructions` (they guide host model behavior)
- ✓ Keep all `tools` (they expand agent capabilities)
- ✓ Keep all `output_type` (they shape results)
- ✓ Keep local `context` (it stays isolated from the model)

## Reasoning, Tool Use, and Feature Support

### Reasoning (Chain-of-Thought)

If the host-provided model supports reasoning features:

- **Direct SDK**: Set `model: "gpt-5.4-o1"` or enable reasoning in model settings
- **Copilot Pro+**: Host enables reasoning based on your subscription tier; use instructions to request detailed analysis

```python
# Copilot Pro+: request reasoning in instructions, not model settings
agent = Agent(
    name="Analyst",
    instructions="Think through the problem step by step before answering.",
    # ↑ Host model applies reasoning if available for your subscription
)
```

### Tool Use

Tool use works the same in both contexts:

```python
# Both Direct SDK and Copilot Pro+
agent = Agent(
    name="Researcher",
    tools=[search_web, fetch_api],
    instructions="Use tools to gather information.",
)
```

## Next Steps

Once model constraints are clear, continue with the rest of agent design:

- **[Agent Definitions (Copilot Pro+ Adapted)](./agent-definitions-copilot-adapted.md)** — shape each specialist cleanly (instructions, tools, structured output)
- **[Running Agents](https://developers.openai.com/api/docs/guides/agents/running-agents)** — understand the runtime loop and streaming behavior
- **[Orchestration and Handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)** — design multi-agent workflows
- **[Using Tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)** — expand agent capabilities with function tools

## Key Principle

In **Copilot Pro+**, model selection is not a tuning lever you pull — it's an operational decision made by GitHub based on your subscription. Your job is to write clear instructions, define focused specialists, and let the host provide the best model it can.

This actually simplifies agent development: you focus on what agents *do* and *know*, not how smart the model is.
