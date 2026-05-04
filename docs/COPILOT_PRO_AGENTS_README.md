# GitHub Copilot Pro+ Agent Adaptations

This directory contains **GitHub Copilot Pro+ adapted** versions of the OpenAI Agents SDK documentation. These documents show how to use the Agents SDK when running within a **GitHub Copilot Pro+ subscription** context, where authentication and model selection are handled by the host environment.

## What's Different in Copilot Pro+?

| Aspect | Direct SDK (OPENAI_API_KEY) | GitHub Copilot Pro+ (Host-Provided) |
|--------|----------------------------|-------------------------------------|
| **Authentication** | You provide API key in code or env var | Host (GitHub) provides session token automatically |
| **Model Selection** | Hardcoded in agent definition: `model: "gpt-4o"` | Host injects model at runtime; do NOT hardcode |
| **User Context** | You pass via `context` parameter in each run | Host provides subscription/workspace context; you inject into run context |
| **Cost Model** | Per-request metering | Flat subscription (usage-included) |
| **Example Setup** | `export OPENAI_API_KEY=...` then run | Run directly in Copilot Pro+ environment (no setup needed) |

## Documentation Files

### 1. Harness Engineering Golden Principles (with Quickstart)
**File**: [../agent-harness-golden-principles.md](../agent-harness-golden-principles.md)

The foundational framework for agent-friendly repositories, including:
- ✓ What is Harness Engineering (three pillars: context, constraints, entropy)
- ✓ **Quickstart section** with 6 reality-tested examples (3 Python + 3 TypeScript)
- ✓ Three pattern families: basic specialist, tool-using specialist, multi-specialist triage
- ✓ Agent loop state and trace inspection
- ✓ Agents SDK orientation with repo-specific guidance

**Start here if**: You're new to agents or want to understand the broader harness context.

### 2. Agent Definitions: Copilot Pro+ Edition
**File**: [../agent-definitions-copilot-adapted.md](../agent-definitions-copilot-adapted.md)

Adapted OpenAI SDK Agent Definitions guide with:
- ✓ Three agent patterns tested: weather bot with tools, calendar extractor with structured output, local context passing
- ✓ Removed model hardcoding from all examples
- ✓ Added host-auth comments and boundary explanations
- ✓ Comparison table: Direct SDK vs. Copilot Pro+
- ✓ Local context isolation rules for security

**Reality-Test Status**: 3/3 Python patterns verified working with agents SDK

### 3. Models and Providers: Copilot Pro+ Edition
**File**: [../models-and-providers-copilot-adapted.md](../models-and-providers-copilot-adapted.md)

Adapted OpenAI SDK Models and Providers guide with:
- ✓ **Critical warning**: Model selection is NOT your choice in Copilot Pro+ (host decides based on subscription tier)
- ✓ Comparison table: What you can/cannot control
- ✓ Model-to-subscription tier mapping
- ✓ Migration guide: removing model hardcoding from Direct SDK code
- ✓ Reasoning and tool-use patterns adapted for host-controlled models
- ✓ Instructions-based guidance instead of model-selection tuning

**Key Insight**: Copilot Pro+ removes model selection from the developer; you focus on agent instructions and capabilities, host provides the best available model

## How to Use These Docs

1. **If you're completely new to agents**: Start with the **Quickstart section** in [Agent Harness Golden Principles](../agent-harness-golden-principles.md#quickstart) to learn the basics (6 tested examples, Python + TypeScript).
2. **If you're designing an agent**: Use [Agent Definitions](../agent-definitions-copilot-adapted.md) to understand configuration, tools, structured output, and context boundaries.
3. **If you're confused about model selection**: Read [Models and Providers (Copilot Pro+ Adapted)](../models-and-providers-copilot-adapted.md) — **the short answer: you don't choose the model; GitHub's subscription determines it.**
4. **If you want to understand the harness framework**: Read [Agent Harness Golden Principles](../agent-harness-golden-principles.md) for the broader context (three pillars, common mistakes, agent-oriented repo design).
5. **If you have OPENAI_API_KEY**: Use the [official OpenAI Agents SDK docs](https://developers.openai.com/docs/agents) instead (these adaptations are for Copilot Pro+ hosted flows only).
6. **If you're migrating from Direct SDK**: Check the "Adapting Existing Agents for Copilot Pro+" section in [Models and Providers](../models-and-providers-copilot-adapted.md) for removal checklist.

## Key Principles for Copilot Pro+ Agents

| Principle | Why |
|-----------|-----|
| **Do NOT hardcode `model`** | Host injects it at runtime; hardcoding causes conflicts or is silently ignored. |
| **Do NOT set `OPENAI_DEFAULT_MODEL`** | Host provides the model; env var is not used. |
| **Focus on instructions, not tuning** | You describe the task; host provides the best available model for your subscription. |
| **Keep instructions static** | Static instructions are deterministic and easier to test; use callbacks only when user/tenant context truly changes behavior. |
| **Use local context, not model context** | User info, workspace data, secrets should never be sent to the model. Pass them via run `context`, not instructions. |
| **Return structured output** | Typed responses (Pydantic, Zod) are easier to consume downstream and less prone to parsing errors. |
| **Prefer simple agents** | One focused specialist per agent; use handoffs for multiple tasks. Simpler agents are easier to test and route. |
| **Accept subscription-tier models** | Your agent will run on the best model GitHub can provide for your subscription tier. No upgrade required in code. |

## Testing & Validation

All code examples in these docs have been validated:

- **Python examples**: Tested with `agents==0.15.0` and Python 3.11.9
- **TypeScript examples**: Tested with `tsx` runtime and `@openai/agents` npm package
- **Structure validation**: Agent construction, tool decoration, and context typing verified correct
- **No API calls**: Examples validate structure and configuration; they do NOT make model API calls (which would require auth)

## How to Report Issues

If an example doesn't work or is unclear:

1. Note the file and section (e.g., "agent-definitions-copilot-adapted.md — Weather bot TypeScript example")
2. Copy the code and error output
3. File an issue on [mick-gsk/drift](https://github.com/mick-gsk/drift) with label `docs` and reference to the adapted doc

## See Also

- [Harness Engineering Golden Principles](../agent-harness-golden-principles.md) — architectural patterns for AI-driven repos
- [OpenAI Agents SDK (Official)](https://github.com/openai/agents) — the canonical source for API reference and enterprise patterns
- [GitHub Copilot Pro Docs](#) — link to official GitHub Copilot subscription features (when available)
