# Contract: Prompt File Structure

**Scope**: `.github/prompts/drift-fix-plan.prompt.md`, `drift-export-report.prompt.md`, `drift-auto-fix-loop.prompt.md`  
**Producer**: Feature implementation (static files committed to repo)  
**Consumers**: VS Code GitHub Copilot Chat (invoked as `/drift-fix-plan` etc.)

---

## Required YAML Frontmatter

```yaml
---
name: drift-<command>
description: >
  <One-sentence description. Must include: trigger verbs, context (drift findings),
  expected outcome. This is the Copilot Chat discovery surface — make it precise.>
---
```

**Rules**:
- `name` MUST match the filename stem exactly (`drift-fix-plan` for `drift-fix-plan.prompt.md`).
- `description` MUST contain at least one trigger verb (e.g., "Use when", "Invoke after").
- No additional frontmatter fields; keep it minimal.

---

## Required Body Sections

Each prompt file MUST contain, in order:

### 1. H1 Title + Purpose Paragraph

```markdown
# Drift: <Action Name>

<One-paragraph purpose. Include: what this prompt does, when to use it,
what prerequisite the user must have completed (e.g., "after running drift analyze").>
```

### 2. Session Context Block

```markdown
## Context

Read `.vscode/drift-session.json`.
If the file does not exist: stop and prompt the user to run `drift analyze` first.
If `analyzed_at` is older than 24 hours: warn with the session age and recommend re-analysis. Do not block.
```

### 3. Workflow Steps

```markdown
## Workflow

1. <Step description with explicit tool call or action>
2. <...>
```

Steps MUST be numbered. Each step MUST reference a concrete tool, command, or artifact.

### 4. Output / Artifacts

```markdown
## Output

- <Artifact 1>: <format and location>
- <Artifact 2>: ...
```

### 5. Next Step Handoff (FR-008)

```markdown
## Next Step

After completing this workflow, continue with:
- **[/drift-<next-command>]** — <one-line description>
```

This creates the chain: fix-plan → auto-fix-loop → export-report (or export-report → share).

---

## Anti-Hallucination Rules

- NEVER reference file paths that may not exist (except `.vscode/drift-session.json` — always check first).
- NEVER reference drift CLI flags not in the current help text.
- NEVER fabricate finding IDs or signal types — read them from session file.
- Every MCP tool call MUST use the correct tool name from the drift MCP server.

---

## Prompt Chain (FR-008)

```
/drift-fix-plan
    └── next: /drift-auto-fix-loop

/drift-auto-fix-loop
    └── next: /drift-export-report

/drift-export-report
    └── next: (done — share externally)
```
