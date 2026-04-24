---
name: evolutionary-model
version: "1.0.0"
description: "Framework for building AI agents that evolve with their owner. Use when: setting up a new agent from scratch, onboarding a team to AI-native workflow, explaining the architecture to others, or auditing an existing agent setup for gaps."
when_to_use: "Use when user asks how to set up an AI agent, how to make an agent smarter over time, how to share the agent framework with others, or when explaining the evolutionary model concept."
---

# Evolutionary Model

> *An AI agent that doesn't learn is just an expensive chatbot.*

## The Core Idea

Most people set up AI assistants once and use them forever the same way. The Evolutionary Model is different: the agent grows smarter with every session, accumulates skills, and becomes increasingly specific to its owner's needs.

The model has three axes of evolution:

```
Memory      → agent remembers decisions, context, preferences
Skills      → agent gains new capabilities over time  
Protocols   → agent behavior becomes more reliable and predictable
```

---

## Architecture

### Layer 0 — Identity
Who the agent is. Fixed at birth, rarely changed.

```
SOUL.md       — personality, values, operating principles
IDENTITY.md   — name, role, emoji, avatar
USER.md       — who the agent serves (name, timezone, preferences)
```

### Layer 1 — Memory
How the agent persists across sessions.

```
memory/SESSION-STATE.md      — current focus (WAL, read first)
memory/YYYY-MM-DD.md         — daily raw log
MEMORY.md                    — curated long-term memory
memory/chat-log-YYYY-MM-DD.jsonl  — conversation history
```

**Key principle:** no mental notes. If it's not written to a file, it doesn't exist after session restart.

### Layer 2 — Skills
What the agent can do. Each skill is a self-contained capability module.

```
skills/
  skill-name/
    SKILL.md        — instructions + when_to_use frontmatter
    scripts/        — executable helpers (bash, python)
    config.json     — user-configurable parameters
    README.md       — human-readable docs
```

**`when_to_use` is critical.** Without it, the agent doesn't know when to activate the skill. Format:
```yaml
---
when_to_use: "Use when user asks for X, Y, or Z."
---
```

### Layer 3 — Protocols
How the agent behaves reliably. Learned from mistakes.

```
AGENTS.md     — operating rules, safety, memory protocol
HEARTBEAT.md  — periodic check-in schedule and format
policy.yaml   — what agent can do without asking (allow/ask/deny)
```

---

## How Evolution Works

### Session → Memory
Every session, the agent:
1. Reads `SESSION-STATE.md` (hot context)
2. Reads today's daily log
3. Works
4. Writes new decisions/insights to daily log
5. Periodically distills into `MEMORY.md`

### Task → Skill
When the agent solves a new type of problem:
1. Documents the solution
2. Creates `skills/task-name/SKILL.md`
3. Adds `when_to_use` so it auto-activates next time

### Mistake → Protocol
When the agent makes a mistake:
1. Analyzes root cause
2. Adds rule to `AGENTS.md` or `SOUL.md`
3. Future sessions inherit the fix

---

## Skill Quality Standards

A skill is production-ready when it has:

- [ ] `when_to_use` frontmatter — agent knows when to use it
- [ ] `description` frontmatter — discoverable in skill catalogs
- [ ] No hardcoded personal context (paths, names, tokens)
- [ ] `config.json` or env vars for user-specific settings
- [ ] `README.md` explaining what it does and how to configure
- [ ] Scripts that work from any machine (no absolute paths)

---

## Starter Kit

Minimum viable agent setup:

```
clawd/
  SOUL.md           — who you are
  IDENTITY.md       — your name
  USER.md           — who you serve
  AGENTS.md         — operating rules
  MEMORY.md         — start empty
  memory/           — create on first run
  skills/           — add as you grow
```

Bootstrap checklist:
1. Fill `USER.md` with owner's name, timezone, communication style
2. Write `SOUL.md` — personality takes 30 minutes, saves 1000 future corrections
3. Pick 3 starter skills from the catalog
4. Run first session — agent reads all files and introduces itself
5. After session: review what the agent wrote to memory files

---

## The Compounding Effect

Day 1:  agent knows your name, timezone, and communication style  
Day 3:  agent knows your projects, key contacts, and decisions made  
Day 7:  agent anticipates needs, runs proactive checks, catches mistakes  
Day 14: agent has accumulated skills specific to your workflow  
Day 30: agent is irreplaceable — it carries institutional knowledge no new model can replicate

This is why the model is called "evolutionary": the value grows non-linearly. Not because the base model gets smarter, but because the accumulated context, skills, and protocols become a moat.

---

## Why Not Just Use ChatGPT?

| | ChatGPT / Standard Assistant | Evolutionary Model |
|---|---|---|
| Memory | Resets every session | Persists across sessions |
| Skills | Fixed capabilities | Grows with use |
| Context | Generic | Specific to you |
| Mistakes | Repeated | Documented + prevented |
| Value over time | Flat | Compounding |
| Portability | Locked to provider | Files you own |

The Evolutionary Model runs on any AI provider. The intelligence isn't in the model — it's in the accumulated files. You own them.

---

## Contributing Skills

Skills are just markdown files. To share a skill:

1. Remove all personal context (names, paths, tokens)
2. Replace with `${VARIABLE}` or `config.json` entries
3. Add `when_to_use` frontmatter
4. Write a `README.md`
5. Submit to [ClaWHub](https://clawhub.com) or share as a repo

---

## See Also

- `SOUL.md` — agent identity template
- `AGENTS.md` — operating protocols
- `HEARTBEAT.md` — proactive check-in system
- Skills catalog: `~/clawd/skills/`
