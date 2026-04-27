# Quickstart: VS Code Copilot Chat Workflow Integration

**Feature**: `002-vscode-copilot-workflow`  
**Audience**: Developer setting up drift in a new project  
**Time to complete**: 3 minutes

---

## Prerequisites

- Desktop VS Code (1.90+) with GitHub Copilot Chat extension
- `drift` installed (`pip install drift-analyzer`)
- A Python project to analyze

---

## Step 1: Initialize `.vscode/settings.json`

Add the following to your `.vscode/settings.json` (create it if it doesn't exist):

```json
{
  "chat.promptFilesLocations": [".github/prompts/"]
}
```

This tells VS Code Copilot Chat to discover prompt files from `.github/prompts/`, which drift adds automatically.

---

## Step 2: Run `drift analyze`

```bash
drift analyze --repo .
```

After analysis completes, you will see:

```
┌─────────────────────── Copilot Chat Handoff ───────────────────────┐
│  Score: 0.42 (B — Acceptable)  •  12 findings (3 high)             │
│                                                                      │
│  Top findings:                                                       │
│  ● [high] pattern_fragmentation — src/myapp/utils.py:42-67          │
│  ...                                                                 │
│                                                                      │
│  Next steps in Copilot Chat:                                         │
│    /drift-fix-plan    /drift-export-report    /drift-auto-fix-loop   │
└──────────────────────────────────────────────────────────────────────┘
```

The analysis context is saved to `.vscode/drift-session.json` (gitignored).

---

## Step 3: Open Copilot Chat and run a workflow prompt

Press `Ctrl+Alt+I` to open Copilot Chat, then type one of:

| Command | What it does |
|---------|-------------|
| `/drift-fix-plan` | Reads your findings and generates a prioritized fix plan |
| `/drift-auto-fix-loop` | Starts an automated fix loop for the top findings |
| `/drift-export-report` | Exports findings as a shareable markdown report |

Each command reads `.vscode/drift-session.json` — no copy-pasting required.

---

## Prompt Chain

The three prompts form a guided workflow:

```
drift analyze
    └── /drift-fix-plan  ──►  /drift-auto-fix-loop  ──►  /drift-export-report
```

---

## What Gets Committed

| File | Committed? |
|------|-----------|
| `.github/prompts/drift-fix-plan.prompt.md` | ✅ Yes — shared with team |
| `.github/prompts/drift-export-report.prompt.md` | ✅ Yes |
| `.github/prompts/drift-auto-fix-loop.prompt.md` | ✅ Yes |
| `.vscode/settings.json` | ✅ Yes — configures Copilot Chat |
| `.vscode/drift-session.json` | ❌ No — gitignored, local only |

Team members share prompt files but have their own local session files.

---

## Troubleshooting

**Prompts not appearing in Copilot Chat**  
Check that `chat.promptFilesLocations` is set in `.vscode/settings.json`. Reload VS Code window (`Ctrl+Shift+P` → "Developer: Reload Window").

**"Session file not found" in Copilot Chat**  
Run `drift analyze --repo .` first to generate `.vscode/drift-session.json`.

**"Session is 25 hours old" warning**  
Re-run `drift analyze` to refresh the session context.
