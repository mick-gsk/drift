# Drift MCP Autopilot Demo

Reproduzierbares 30-Minuten-Demo: drift MCP-Server analysiert ein externes Repository,
Copilot Agent Mode behebt alle priorisierten Findings über die Task-Queue,
`drift_diff` verifiziert, `drift_session_end` exportiert einen strukturierten Audit-Trail.

## Dateien

| Datei | Zweck |
|-------|-------|
| [`audit-trail.schema.json`](audit-trail.schema.json) | JSON Schema für den Audit-Trail |
| [`audit-trail.example.json`](audit-trail.example.json) | Beispiel-Audit-Trail (openclaw-basiert) |
| [`mcp.template.json`](mcp.template.json) | `.vscode/mcp.json` Template für externe Repos |
| [`copilot-instructions.template.md`](copilot-instructions.template.md) | Agent-Steuerung für Copilot Agent Mode |
| [`demo-script.md`](demo-script.md) | Terminal-Demo-Skript mit Zeitmarken |

## Prompt

Der zugehörige Prompt liegt unter [`.github/prompts/drift-mcp-autopilot-demo.prompt.md`](../../.github/prompts/drift-mcp-autopilot-demo.prompt.md).

## Quick-Start

```bash
# 1. Ziel-Repo klonen
git clone https://github.com/<owner>/<repo> && cd <repo>

# 2. drift installieren
pip install drift-analyzer[mcp]

# 3. MCP-Konfiguration kopieren
mkdir -p .vscode
cp /path/to/drift/demos/mcp-autopilot-demo/mcp.template.json .vscode/mcp.json

# 4. Agent-Instructions kopieren (optional)
mkdir -p .github
cp /path/to/drift/demos/mcp-autopilot-demo/copilot-instructions.template.md .github/copilot-instructions.md

# 5. VS Code öffnen, Agent Mode starten
code .
# → "Start drift autopilot session and fix all critical findings"
```

## Voraussetzungen

- Python 3.10+
- `drift-analyzer[mcp]` (keine weiteren Dependencies)
- Copilot Pro+ Subscription (kein separater LLM-API-Key)
- VS Code mit Copilot Agent Mode
- Git-Repository als Analyseziel

## HN-belegbare Metriken

Aus `drift-audit.json` direkt ablesbar:

1. **Score-Delta** → `demo_run.score_delta`
2. **Fix-Rate** → `findings_summary.total_fixed / total_identified`
3. **Dauer** → `demo_run.duration_seconds` (< 1800s)
