---
name: self-improving-agent
description: "Log learnings, errors, and corrections to .learnings/ for continuous improvement. Use when: (1) A command or operation fails unexpectedly, (2) User corrects the agent, (3) A knowledge gap is identified, (4) A better approach is found. Captures corrections, insights, errors, and feature requests; promotes broadly applicable learnings to project memory files."
argument-hint: "Describe what happened: error, correction, knowledge gap, or feature request."
---

# Self-Improvement Skill

Log learnings and errors to markdown files for continuous improvement. Coding
agents can later process these into fixes, and important learnings get promoted to
project memory.

Source: https://clawhub.ai/pskoett/self-improving-agent (v3.0.16, MIT-0)

## First-Use Initialisation

Before logging anything, ensure the `.learnings/` directory and files exist in the project or workspace root. If any are missing, create them:

```
mkdir -p .learnings
[ -f .learnings/LEARNINGS.md ] || printf "# Learnings\n\nCorrections, insights, and knowledge gaps captured during development.\n\n**Categories**: correction | insight | knowledge_gap | best_practice\n\n---\n" > .learnings/LEARNINGS.md
[ -f .learnings/ERRORS.md ] || printf "# Errors\n\nCommand failures and integration errors.\n\n---\n" > .learnings/ERRORS.md
[ -f .learnings/FEATURE_REQUESTS.md ] || printf "# Feature Requests\n\nCapabilities requested by the user.\n\n---\n" > .learnings/FEATURE_REQUESTS.md
```

Never overwrite existing files. This is a no-op if `.learnings/` is already initialised.

Do not log secrets, tokens, private keys, environment variables, or full source/config files unless the user explicitly asks for that level of detail. Prefer short summaries or redacted excerpts over raw command output or full transcripts.

## Quick Reference

| Situation | Action |
|---|---|
| Command/operation fails | Log to `.learnings/ERRORS.md` |
| User corrects you | Log to `.learnings/LEARNINGS.md` with category `correction` |
| User wants missing feature | Log to `.learnings/FEATURE_REQUESTS.md` |
| API/external tool fails | Log to `.learnings/ERRORS.md` with integration details |
| Knowledge was outdated | Log to `.learnings/LEARNINGS.md` with category `knowledge_gap` |
| Found better approach | Log to `.learnings/LEARNINGS.md` with category `best_practice` |
| Simplify/Harden recurring patterns | Log/update `.learnings/LEARNINGS.md` with `Source: simplify-and-harden` and a stable `Pattern-Key` |
| Similar to existing entry | Link with **See Also**, consider priority bump |
| Broadly applicable learning | Promote to `CLAUDE.md`, `AGENTS.md`, and/or `.github/copilot-instructions.md` |

## Logging Format

### Learning Entry

Append to `.learnings/LEARNINGS.md`:

```
## [LRN-YYYYMMDD-XXX] category

**Logged**: ISO-8601 timestamp
**Priority**: low | medium | high | critical
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
One-line description of what was learned

### Details
Full context: what happened, what was wrong, what's correct

### Suggested Action
Specific fix or improvement to make

### Metadata
- Source: conversation | error | user_feedback
- Related Files: path/to/file.ext
- Tags: tag1, tag2
- See Also: LRN-20250110-001 (if related to existing entry)
- Pattern-Key: simplify.dead_code | harden.input_validation (optional, for recurring-pattern tracking)
- Recurrence-Count: 1 (optional)
- First-Seen: 2025-01-15 (optional)
- Last-Seen: 2025-01-15 (optional)

---
```

### Error Entry

Append to `.learnings/ERRORS.md`:

```
## [ERR-YYYYMMDD-XXX] skill_or_command_name

**Logged**: ISO-8601 timestamp
**Priority**: high
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Summary
Brief description of what failed

### Error
Actual error message or output

### Context
- Command/operation attempted
- Input or parameters used
- Environment details if relevant
- Summary or redacted excerpt of relevant output (avoid full transcripts and secret-bearing data by default)

### Suggested Fix
If identifiable, what might resolve this

### Metadata
- Reproducible: yes | no | unknown
- Related Files: path/to/file.ext
- See Also: ERR-20250110-001 (if recurring)

---
```

### Feature Request Entry

Append to `.learnings/FEATURE_REQUESTS.md`:

```
## [FEAT-YYYYMMDD-XXX] capability_name

**Logged**: ISO-8601 timestamp
**Priority**: medium
**Status**: pending
**Area**: frontend | backend | infra | tests | docs | config

### Requested Capability
What the user wanted to do

### User Context
Why they needed it, what problem they're solving

### Complexity Estimate
simple | medium | complex

### Suggested Implementation
How this could be built, what it might extend

### Metadata
- Frequency: first_time | recurring
- Related Features: existing_feature_name

---
```

## ID Generation

Format: `TYPE-YYYYMMDD-XXX`

- TYPE: `LRN` (learning), `ERR` (error), `FEAT` (feature)
- YYYYMMDD: Current date
- XXX: Sequential number or random 3 chars (e.g., `001`, `A7B`)

Examples: `LRN-20250115-001`, `ERR-20250115-A3F`, `FEAT-20250115-002`

## Resolving Entries

When an issue is fixed, update the entry:

- Change `**Status**: pending` → `**Status**: resolved`
- Add resolution block after Metadata:

```
### Resolution
- **Resolved**: 2025-01-16T09:00:00Z
- **Commit/PR**: abc123 or #42
- **Notes**: Brief description of what was done
```

Other status values:
- `in_progress` - Actively being worked on
- `wont_fix` - Decided not to address (add reason in Resolution notes)
- `promoted` - Elevated to `CLAUDE.md`, `AGENTS.md`, or `.github/copilot-instructions.md`

## Promoting to Project Memory

When a learning is broadly applicable (not a one-off fix), promote it to permanent project memory.

### When to Promote

- Learning applies across multiple files/features
- Knowledge any contributor (human or AI) should know
- Prevents recurring mistakes
- Documents project-specific conventions

### Promotion Targets

| Target | Use for |
|---|---|
| `CLAUDE.md` | Project facts, conventions, gotchas for all Claude interactions |
| `AGENTS.md` | Agent-specific workflows, tool usage patterns, automation rules |
| `.github/copilot-instructions.md` | Project context and conventions for GitHub Copilot |

### How to Promote

1. Distill the learning into a concise rule or fact
2. Add to appropriate section in target file (create file if needed)
3. Update original entry: Change `**Status**: pending` → `**Status**: promoted` and add `**Promoted**: <target file>`

## Recurring Pattern Detection

If logging something similar to an existing entry:

- Search first: `grep -r "keyword" .learnings/`
- Link entries: Add `**See Also**: ERR-20250110-001` in Metadata
- Bump priority if issue keeps recurring
- Consider systemic fix: Recurring issues often indicate missing documentation (→ promote to `CLAUDE.md`) or missing automation (→ add to `AGENTS.md`)

## Detection Triggers

Automatically log when you notice:

**Corrections** (→ learning with `correction` category):
- "No, that's not right..."
- "Actually, it should be..."
- "That's outdated..."

**Feature Requests** (→ feature request):
- "Can you also..."
- "I wish you could..."
- "Is there a way to..."

**Knowledge Gaps** (→ learning with `knowledge_gap` category):
- User provides information you didn't know
- Documentation you referenced is outdated
- API behavior differs from your understanding

**Errors** (→ error entry):
- Command returns non-zero exit code
- Exception or stack trace
- Unexpected output or behavior
- Timeout or connection failure

## Priority Guidelines

| Priority | When |
|---|---|
| critical | Blocks core functionality, data loss risk, security issue |
| high | Significant impact, affects common workflows, recurring issue |
| medium | Moderate impact, workaround exists |
| low | Minor inconvenience, edge case, nice-to-have |

## Area Tags

| Tag | Use for |
|---|---|
| frontend | UI, components, client-side code |
| backend | API, services, server-side code |
| infra | CI/CD, deployment, Docker, cloud |
| tests | Test files, testing utilities, coverage |
| docs | Documentation, comments, READMEs |
| config | Configuration files, environment, settings |

## Best Practices

- Log immediately — context is freshest right after the issue
- Be specific — future agents need to understand quickly
- Include reproduction steps — especially for errors
- Link related files — makes fixes easier
- Suggest concrete fixes — not just "investigate"
- Use consistent categories — enables filtering
- Promote aggressively — if in doubt, add to `CLAUDE.md` or `.github/copilot-instructions.md`
- Review regularly — stale learnings lose value

## Gitignore Options

Keep learnings local (per-developer):
```
.learnings/
```

Track learnings in repo (team-wide): Don't add to `.gitignore` — learnings become shared knowledge.

Hybrid (track templates, ignore entries):
```
.learnings/*.md
!.learnings/.gitkeep
```

## Multi-Agent Support (GitHub Copilot)

For GitHub Copilot, there is no hook support. Activation is manual:

Add to `.github/copilot-instructions.md`:

```
## Self-Improvement

After solving non-obvious issues, consider logging to `.learnings/`:
1. Use format from self-improvement skill
2. Link related entries with See Also
3. Promote high-value learnings to skills

Ask in chat: "Should I log this as a learning?"
```
