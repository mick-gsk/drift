---
name: "Drift MCP Autopilot Demo"
description: "Reproduzierbares 30-Minuten-Demo: MCP-Server analysiert ein externes Repo, Copilot Agent Mode behebt alle kritischen Findings ueber die Task-Queue, drift_diff verifiziert, drift_session_end exportiert Audit-Trail. Keywords: MCP demo, autopilot, fix-loop, task queue, audit trail, Copilot Agent Mode."
---

# Drift MCP Autopilot Demo

Vollstaendig ausfuehrbares Demo-Szenario: drift analysiert ein externes Repository ueber den MCP-Server, Copilot Agent Mode behebt alle priorisierten Findings automatisch ueber die Task-Queue und exportiert einen strukturierten Audit-Trail.

> **Pflicht:** Vor Ausfuehrung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Prompt:** `.github/prompts/drift-fix-loop.prompt.md` (Inner-Loop-Workflow)
- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Skill:** `.github/skills/drift-effective-usage/SKILL.md`
- **Skill:** `.github/skills/drift-commit-push/SKILL.md`
- **MCP-Server:** `src/drift/mcp_server.py`
- **Session-Management:** `src/drift/session.py`
- **Audit-Schema:** `demos/copilot-autopilot/audit-trail.schema.json`

## Voraussetzungen

- Python 3.10+
- `pip install drift-analyzer[mcp]` (keine weiteren Dependencies)
- Copilot Pro+ Subscription (kein separater LLM-API-Key)
- VS Code mit Copilot Agent Mode
- Git-Repository als Analyseziel (muss `git log` unterstuetzen)

## Ziel

Bestimme, ob der drift MCP-Autopilot-Workflow ein externes Repository innerhalb von 30 Minuten analysieren, alle priorisierten Findings beheben und einen verifizierbaren Audit-Trail erzeugen kann.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn:
- `drift_session_start(autopilot=true)` erfolgreich N Tasks identifiziert hat
- Alle Tasks via `drift_task_claim` → Fix → `drift_nudge` → `drift_task_complete` durchlaufen wurden
- `drift_diff(uncommitted=true)` keine neuen HIGH/CRITICAL-Findings zeigt
- `drift_session_end` ein Score-Delta zurueckgibt
- `drift-audit.json` als strukturiertes Artefakt vorliegt
- Alle Diffs via `git diff --stat` sichtbar sind BEVOR ein Commit erfolgt
- Gesamtdauer unter 30 Minuten liegt

## Bewertungs-Labels

- **Ergebnis:** `pass` / `review` / `fail`
- **Phasen-Status:** `completed` / `skipped` / `blocked`

## Artefakte

Erstelle Artefakte unter `work_artifacts/mcp_demo_<YYYY-MM-DD>/`:

1. `drift-audit.json` — Strukturierter Audit-Trail (Schema: `demos/copilot-autopilot/audit-trail.schema.json`)
2. `session-log.md` — Chronologisches Protokoll aller MCP-Tool-Aufrufe mit Zeitstempeln
3. `summary.md` — Kompaktbericht mit 3 HN-belegbaren Metriken

---

## Phase 0 — Setup (Budget: ~3 min)

### 0.1 Repository klonen und drift installieren

```bash
git clone <REPO_URL> && cd <REPO_NAME>
pip install drift-analyzer[mcp]
drift --version   # Version dokumentieren
```

### 0.2 MCP-Konfiguration schreiben

Erstelle `.vscode/mcp.json` im Ziel-Repository:

```json
{
  "servers": {
    "drift": {
      "type": "stdio",
      "command": "drift",
      "args": ["mcp", "--serve"]
    }
  }
}
```

Falls `drift` nicht im PATH: `"command": "python", "args": ["-m", "drift", "mcp", "--serve"]`

### 0.3 Smoke-Test

```
drift_validate(path=".")
```

**Abbruchkriterium:** `valid != true` → Setup-Probleme loesen, bevor der Workflow beginnt.

---

## Phase 1 — Autopilot-Scan (Budget: ~5 min)

### 1.1 Session starten

```
drift_session_start(
    path=".",
    autopilot=true,
    autopilot_payload="summary",
    ttl_seconds=3600
)
```

**Output-Checks:**
- `status == "ok"`
- `session_id` notieren (fuer alle weiteren Aufrufe)
- `autopilot.task_count >= 1`
- `autopilot.drift_score` notieren als `score_before`

**Abbruchkriterium:** `task_count == 0` → Repo hat keine actionable Findings. Demo endet mit `pass` (drift bestaetigt saubere Architektur).

### 1.2 Findings dokumentieren

Aus der Autopilot-Response extrahieren und in `session-log.md` festhalten:
- `drift_score`
- `task_count`
- `top_signals` (Signal-Kuerzel + Anzahl)
- `tasks_preview` (Top-3 Tasks mit Signal, Severity, Datei)

---

## Phase 2 — Fix-Loop (Budget: ~18 min)

Fuer jeden Task den folgenden Zyklus ausfuehren. **Immer nur ein Task gleichzeitig.**

### 2.1 Task claimen

```
drift_task_claim(
    session_id="<SESSION_ID>",
    agent_id="copilot"
)
```

**Output-Checks:**
- `status == "claimed"` → weiter mit 2.2
- `status == "no_tasks_available"` → BREAK, weiter zu Phase 3

**Abbruchkriterium bei Fehler:** `status == "error"` → `session-log.md` dokumentieren, naechsten Task versuchen.

### 2.2 Fix implementieren

Dateien gemaess `task.action` und `task.constraints` editieren.

**Batch-Regel:** Wenn `task.batch_eligible == true`, alle Dateien in `task.affected_files_for_pattern` im selben Turn bearbeiten.

### 2.3 Nudge — schnelles Feedback

```
drift_nudge(
    session_id="<SESSION_ID>",
    changed_files="<kommaseparierte_pfade>"
)
```

**Entscheidungslogik:**

| `direction` | `safe_to_commit` | Aktion |
|---|---|---|
| `improving` | `true` | Weiter zu 2.4 |
| `stable` | `true` | Weiter zu 2.4 |
| `degrading` | `false` | Aenderungen reverten, alternativen Fix versuchen (max. 1 Retry) |
| `degrading` | `true` | Warnung in `session-log.md`, weiter zu 2.4 |

**Abbruchkriterium:** 2× hintereinander `degrading` fuer denselben Task → Task ueberspringen, `drift_task_release` aufrufen.

### 2.4 Task abschliessen

```
drift_task_complete(
    session_id="<SESSION_ID>",
    agent_id="copilot",
    task_id="<TASK_ID>"
)
```

### 2.5 Per-Task Audit-Daten sammeln

Nach jedem abgeschlossenen Task die folgenden Daten fuer `drift-audit.json` festhalten:

```json
{
  "task_id": "<aus claim>",
  "signal": "<aus task.signal>",
  "severity": "<aus task.severity>",
  "fix_description": "<aus task.action, 1 Satz>",
  "affected_files": ["<aus task.file oder affected_files_for_pattern>"],
  "batch_eligible": false,
  "nudge_direction": "<aus nudge.direction>",
  "nudge_delta": 0.0
}
```

**Dann zurueck zu 2.1** fuer den naechsten Task.

---

## Phase 3 — Verifikation (Budget: ~2 min)

### 3.1 Abschluss-Diff

```
drift_diff(
    session_id="<SESSION_ID>",
    uncommitted=true
)
```

**Output-Checks:**
- `accept_change == true` → Verifikation bestanden
- `new_finding_count == 0` → keine Regressionen
- `new_high_or_critical == 0` → keine neuen kritischen Findings

**Bei `accept_change == false`:** Blocking-Reasons dokumentieren und bewerten, ob manueller Eingriff noetig ist.

### 3.2 Git-Diff anzeigen (KEIN Auto-Commit)

```bash
git diff --stat
git diff              # Vollstaendiger Diff fuer Review
```

Diff-Output sichtbar machen und auf User-Approval warten.

---

## Phase 4 — Session beenden und Audit-Trail exportieren (Budget: ~2 min)

### 4.1 Session beenden

```
drift_session_end(session_id="<SESSION_ID>")
```

**Extrahieren:**
- `score_start` / `score_end` / `score_delta`
- `duration_seconds`
- `orchestration_metrics` (vollstaendig)
- `timing` (vollstaendig)

### 4.2 Audit-Trail assemblieren

Aus den gesammelten Daten (Phase 1 + Phase 2 + Phase 3 + Phase 4) das `drift-audit.json` gemaess Schema zusammenbauen.

Die drei belegbaren Kernmetriken:

1. **Score-Delta:** `demo_run.score_delta` — quantitative Verbesserung
2. **Fix-Rate:** `findings_summary.total_fixed / total_critical` — Anteil behobener Findings
3. **Dauer:** `demo_run.duration_seconds` — unter 1800 Sekunden

### 4.3 Commit (nur nach User-Approval)

```bash
git add -A
git commit -m "fix: resolve N drift findings (autopilot demo)"
```

---

## Anti-Patterns

| Anti-Pattern | Problem | Stattdessen |
|---|---|---|
| `drift_scan` nach jeder Aenderung | ~3-5s statt ~0.2s | `drift_nudge` verwenden |
| `session_start` ohne `autopilot=true` | 4 Roundtrips statt 1 | `autopilot=true` setzen |
| `fix_plan(max_tasks=5)` im Loop | grosse Response, unnuetzlich | `max_tasks=1` im Loop |
| Kein `session_id` weitergeben | Kontext-Verlust | Immer `session_id` uebergeben |
| Auto-Commit ohne Review | Blindes Vertrauen | `git diff --stat` zeigen, User-Approval abwarten |
| Mehrere Tasks parallel | Unklar welche Aenderung wirkt | Ein Task pro Iteration |

## Verhalten bei `agent_instruction` in Responses

Jede MCP-Tool-Response enthaelt `agent_instruction` und `next_tool_call`. Diese Felder befolgen — sie passen zum aktuellen Session-Zustand.
