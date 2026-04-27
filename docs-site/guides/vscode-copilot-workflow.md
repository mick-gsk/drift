# Drift in VS Code Copilot Chat — Workflow Guide

After running `drift analyze`, drift writes a compact session file to
`.vscode/drift-session.json` and displays a **Copilot Chat Handoff** panel in the
terminal. The panel lists the top findings and three slash commands you can invoke
directly in VS Code Copilot Chat — no extension required.

## Prerequisites

- VS Code with GitHub Copilot Chat enabled
- drift installed in the project's virtual environment (or globally)

No additional plugins or marketplace extensions are needed.

## Setup (one-time per repository)

### 1. Register the prompt directory

Add the following to your `.vscode/settings.json`:

```json
{
  "chat.promptFilesLocations": [".github/prompts/"]
}
```

This makes the drift prompt files discoverable in VS Code Copilot Chat as slash
commands.

### 2. Run drift analyze

```bash
drift analyze --repo .
```

At the end of the output you will see a **Copilot Chat Handoff** panel:

```
┌─────────────────────── Copilot Chat Handoff ──────────────────────────┐
│  Severity  Signal                    File                  Reason      │
│  high      pattern_fragmentation     src/core/engine.py    …           │
│  medium    module_dependency_score   src/utils/helpers.py  …           │
│                                                                         │
│  Next: /drift-fix-plan  /drift-export-report  /drift-auto-fix-loop    │
└─────────────────────────────────────────────────────────────────────────┘
```

The session file `.vscode/drift-session.json` is written automatically and is
excluded from version control via `.gitignore`.

## Available slash commands

Open VS Code Copilot Chat (++ctrl+alt+i++) and type one of the following:

| Command | Purpose |
|---|---|
| `/drift-fix-plan` | Generate a prioritized, actionable fix plan from the top findings |
| `/drift-export-report` | Produce a self-contained markdown report to share or attach to a ticket |
| `/drift-auto-fix-loop` | Step through each finding one at a time with explicit confirm/skip gates |

### Recommended workflow

```
drift analyze
    │
    └─► /drift-fix-plan          ← what needs fixing and how
              │
              └─► /drift-auto-fix-loop  ← apply fixes with confirmation
                        │
                        └─► /drift-export-report  ← document the result
```

## Session file

All three slash commands read `.vscode/drift-session.json`. This file holds:

- `drift_score` and `grade` from the most recent analysis
- `top_findings` — up to 5 findings ordered by severity, then impact
- `findings_total`, `critical_count`, `high_count`
- `analyzed_at` — ISO 8601 UTC timestamp

If you run `drift analyze` again, the file is overwritten automatically.

!!! warning "Stale session"
    If `analyzed_at` is older than 24 hours, the slash commands warn you and
    recommend re-running `drift analyze`. They do not block execution.

If `.vscode/drift-session.json` does not exist when you invoke a slash command,
Copilot Chat will prompt you to run `drift analyze` first.

## JSON output

If you redirect analysis to a file, the session is **not** written and the handoff
panel is **not** shown:

```bash
drift analyze --format json --output findings.json   # no session file written
drift analyze --format json                          # session file + copilot_handoff key in stdout
```

When running without `--output`, JSON output includes a `copilot_handoff` key at
the top level so downstream automation can consume the handoff block directly.

## MCP vs. Copilot Chat handoff

Both integration paths serve different use cases:

| | MCP (Cursor / VS Code Agent) | Copilot Chat Handoff |
|---|---|---|
| Requires MCP server | Yes | No |
| Interactive tool calls | Yes | No |
| Entry point | Agent chat, inline completion | Slash commands (`/drift-fix-plan`) |
| Session persistence | Per-session | `.vscode/drift-session.json` |
| Best for | Automated fix loops in agent mode | Manual review + guided remediation |

Use MCP when you want the agent to drive the full analysis loop. Use the Copilot
Chat handoff when you want to keep control and step through findings yourself.

## Related pages

- [Cursor MCP Setup](cursor-mcp-setup.md)
- [Integrations](../integrations.md)
- [Quick Start](../getting-started/quickstart.md)
