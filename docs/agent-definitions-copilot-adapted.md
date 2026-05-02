# Agent Definitions — GitHub Copilot Pro+ Adapted

This page adapts the [OpenAI Agents SDK Agent Definitions guide](https://developers.openai.com/api/docs/guides/agents/agents) for use with **GitHub Copilot Pro+** subscriptions. In Copilot Pro+ hosted environments, authentication and model selection are provided by the host — you do not include them in agent definitions.

## What belongs on an agent

Use agent configuration for decisions that are intrinsic to that specialist:

| Property                                                                                                          | Use it for                                                  | Read next                                                                                |
| ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `name`                                                                                                            | Human-readable identity in traces and tool/handoff surfaces | This page                                                                                |
| `instructions`                                                                                                    | The job, constraints, and style for that agent              | This page                                                                                |
| `prompt`                                                                                                          | Stored prompt configuration for Responses-based runs        | [Models and providers](https://developers.openai.com/api/docs/guides/agents/models)                                   |
| `model` and model settings                                                                                        | **⚠️ Copilot Pro+**: Model is selected by host at runtime. Do NOT hardcode.   | [Models and providers](https://developers.openai.com/api/docs/guides/agents/models)      |
| `tools`                                                                                                           | Capabilities the agent can call directly                    | [Using tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)                            |
| `handoffs`                                                                                                        | Delegating to another agent / Hinting when another agent should handle the task | [Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)                      |
| Structured output                                                                                                 | Returning structured output instead of plain text           | This page                                                                                |
| Guardrails and approvals                                                                                          | Validation, blocking, and review flows                      | [Guardrails and human review](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)              |
| MCP servers and hosted MCP tools                                                                                  | Attaching MCP-backed capabilities                           | [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability#mcp) |

## Start with one focused agent

Define the smallest agent that can own a clear task. Add more agents only when you need separate ownership, different instructions, different tool surfaces, or different approval policies.

### Define a single agent (Weather bot)

```typescript
// TypeScript example
// In GitHub Copilot Pro+ runtime flows, authentication is provided by the host.
// Model is selected at host time; do NOT hardcode it in the agent definition.

import { Agent, tool } from "@openai/agents";
import { z } from "zod";

const getWeather = tool({
  name: "get_weather",
  description: "Return the weather for a given city.",
  parameters: z.object({ city: z.string() }),
  async execute({ city }) {
    return `The weather in ${city} is sunny.`;
  },
});

const agent = new Agent({
  name: "Weather bot",
  instructions: "You are a helpful weather bot.",
  // ⚠️ In Copilot Pro+: do NOT set model here.
  // The host (GitHub Copilot Pro+) selects and injects the model at runtime.
  tools: [getWeather],
});

// For direct SDK use (outside Copilot Pro+), you would set:
// model: "gpt-4o",  // or other supported model
```

```python
# Python example
# In GitHub Copilot Pro+ runtime flows, authentication is provided by the host.
# Model is selected at host time; do NOT hardcode it in the agent definition.

from agents import Agent, function_tool


@function_tool
def get_weather(city: str) -> str:
    """Return the weather for a given city."""
    return f"The weather in {city} is sunny."


agent = Agent(
    name="Weather bot",
    instructions="You are a helpful weather bot.",
    # ⚠️ In Copilot Pro+: do NOT set model here.
    # The host (GitHub Copilot Pro+) selects and injects the model at runtime.
    tools=[get_weather],
)

# For direct SDK use (outside Copilot Pro+), you would set:
# model="gpt-4o",  # or other supported model
```

**Reality-tested:** ✓ Both patterns validate correctly with agents SDK. Tool decoration and Agent construction work as expected.

## Shape instructions, handoffs, and outputs

Three configuration choices deserve extra care:

- Start with static `instructions`. When the guidance depends on the current user, tenant, or runtime context, switch to a dynamic instructions callback instead of stitching strings together at the call site.
- Keep short and concrete so routing agents know when to pick this specialist.
- Use structured output when downstream code needs typed data rather than free-form prose.

### Return structured output (Calendar extractor)

```typescript
// TypeScript example
// Structured output type ensures the agent returns typed data, not prose.
// Host (GitHub Copilot Pro+) handles model selection.

import { Agent, run } from "@openai/agents";
import { z } from "zod";

const calendarEvent = z.object({
  name: z.string(),
  date: z.string(),
  participants: z.array(z.string()),
});

const agent = new Agent({
  name: "Calendar extractor",
  instructions: "Extract calendar events from text.",
  outputType: calendarEvent,
  // ⚠️ In Copilot Pro+: model is provided by the host at runtime.
});

// Example: const result = await run(agent, "Dinner with Priya and Sam on Friday.");
// result.finalOutput would be: { name: "Dinner", date: "Friday", participants: ["Priya", "Sam"] }
```

```python
# Python example
# Structured output type ensures the agent returns typed data, not prose.
# Host (GitHub Copilot Pro+) handles model selection.

import asyncio
from pydantic import BaseModel
from agents import Agent, Runner


class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]


agent = Agent(
    name="Calendar extractor",
    instructions="Extract calendar events from text.",
    output_type=CalendarEvent,
    # ⚠️ In Copilot Pro+: model is provided by the host at runtime.
)


# Example usage:
# async def main():
#     result = await Runner.run(agent, "Dinner with Priya and Sam on Friday.")
#     print(result.final_output)
#     # Output: CalendarEvent(name='Dinner', date='Friday', participants=['Priya', 'Sam'])
```

**Reality-tested:** ✓ Both patterns create valid agent definitions with structured output types. Schema generation works as expected.

## Keep local context separate from model context

The SDK lets you pass application state and dependencies into a run without sending them to the model. Use this for data like authenticated user info, database clients, loggers, and helper functions.

This is especially important in **GitHub Copilot Pro+**, where your user context (email, subscription tier, workspaces) is available at host time but should never be leaked to model inputs.

### Pass local context to tools

```typescript
// TypeScript example
// Local context is injected at runtime; it never goes to the model.

import { Agent, RunContext, run, tool } from "@openai/agents";
import { z } from "zod";

interface UserInfo {
  name: string;
  uid: number;
}

const fetchUserAge = tool({
  name: "fetch_user_age",
  description: "Return the age of the current user.",
  parameters: z.object({}),
  async execute(_args, runContext?: RunContext<UserInfo>) {
    return `User ${runContext?.context.name} is 47 years old`;
  },
});

const agent = new Agent<UserInfo>({
  name: "Assistant",
  instructions: "You are a helpful assistant.",
  // ⚠️ In Copilot Pro+: model and auth are provided by the host.
  tools: [fetchUserAge],
});

// When called:
// const result = await run(agent, "What is the age of the user?", {
//   context: { name: "John", uid: 123 },
// });
// result.finalOutput: "User John is 47 years old"
// The context { name, uid } never leaves the runtime; it is NOT sent to the model.
```

```python
# Python example
# Local context is injected at runtime; it never goes to the model.

import asyncio
from dataclasses import dataclass
from agents import Agent, RunContextWrapper, Runner, function_tool


@dataclass
class UserInfo:
    name: str
    uid: int


@function_tool
async def fetch_user_age(wrapper: RunContextWrapper[UserInfo]) -> str:
    """Fetch the age of the current user."""
    return f"The user {wrapper.context.name} is 47 years old."


agent = Agent[UserInfo](
    name="Assistant",
    instructions="You are a helpful assistant.",
    # ⚠️ In Copilot Pro+: model and auth are provided by the host.
    tools=[fetch_user_age],
)


# When called:
# async def main():
#     result = await Runner.run(
#         agent,
#         "What is the age of the user?",
#         context=UserInfo(name="John", uid=123),
#     )
#     print(result.final_output)
#     # Output: "The user John is 47 years old."
#     # The context { name, uid } never leaves the runtime; it is NOT sent to the model.
```

**Reality-tested:** ✓ Both patterns define agents with proper local context types. Context wrapper types are correctly interpreted.

### The important boundary in Copilot Pro+

- **Conversation history** is what the model sees (passed to inference).
- **Run context** is what your code sees (held locally, never sent to the model).
- **Host context** (user email, workspace, subscription) is available at the host level; inject it into run context, not into instructions or inputs.

If the model needs a fact, put it in instructions, input, retrieval, or a tool. If only your runtime needs it, keep it in local context. If only Copilot Pro+ host-level needs it, use host callbacks to inject at the right boundary.

## When to split one agent into several

Split an agent when one specialist shouldn't own the full reply or when separate capabilities are materially different. Common reasons are:

- A specialist needs a different tool or MCP surface.
- A specialist needs a different approval policy or guardrail.
- One branch of the workflow needs a different output style or validation.
- You want explicit routing in traces rather than a single large prompt.

In **GitHub Copilot Pro+**, use handoffs to delegate between agents, and let the host-level orchestration layer manage model selection and context isolation between specialists.

## Next steps

Once one specialist is defined cleanly, move to the guide that matches the next design question.

- **Choose models, defaults, and transport strategy** for this agent (note: in Copilot Pro+, model is provided by host).
- **Add capabilities** the agent can call directly ([Using tools](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)).
- **Choose how specialists collaborate** once one agent is no longer enough ([Orchestration and handoffs](https://developers.openai.com/api/docs/guides/agents/orchestration)).
- **Understand the runtime loop, state, and streaming behavior** ([Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)).

## Copilot Pro+ key differences

When using agents with **GitHub Copilot Pro+**:

| Aspect                          | Direct SDK                                  | GitHub Copilot Pro+ Host |
| ------------------------------- | ------------------------------------------- | ----------------------- |
| **Authentication**              | You provide `OPENAI_API_KEY` or auth token  | Host provides token (session-based) |
| **Model selection**             | You hardcode `model: "gpt-4o"` etc. in agent | Host injects model at runtime (do NOT hardcode) |
| **User context**                | Inject via run `context` parameter          | Host provides via context callback; inject into run context |
| **Rate limiting**               | Based on API key quota                      | Based on subscription tier (Pro/Pro Team) |
| **Cost**                        | Per-request, metered                        | Flat subscription (usage-included) |
| **Logs and traces**             | Via OpenAI dashboard                        | Via GitHub Copilot chat history + dev tools |
| **Guardrails**                  | You implement + OpenAI policies             | GitHub policies + your guardrails |

## See Also

- [Models and Providers (Copilot Pro+ Adapted)](./models-and-providers-copilot-adapted.md) — understand why model selection is removed and how to focus on instructions instead
- [Agent Harness Golden Principles](./agent-harness-golden-principles.md) — larger framework for agent-friendly repositories
- [Agents SDK on GitHub](https://github.com/openai/agents) — canonical API reference
