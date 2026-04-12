# Demo-Skript: Drift MCP Autopilot (30-Minuten-Budget)

Dieses Skript ist für ein asciinema-Recording oder eine Live-Demo ausgelegt.
Jeder Schritt hat eine Zeitmarke (T+mm:ss) und den erwarteten Output.

---

## Phase 0 — Setup (T+00:00 bis T+03:00)

```
T+00:00  # Repo klonen
         git clone https://github.com/openclaw/openclaw && cd openclaw

T+00:30  # drift installieren
         pip install drift-analyzer[mcp]

T+01:00  # Version prüfen
         drift --version
         # → drift-analyzer 2.9.x

T+01:15  # MCP-Konfiguration schreiben
         mkdir -p .vscode
         cat > .vscode/mcp.json << 'EOF'
         {
           "servers": {
             "drift": {
               "type": "stdio",
               "command": "drift",
               "args": ["mcp", "--serve"]
             }
           }
         }
         EOF

T+01:30  # VS Code öffnen
         code .

T+02:00  # Copilot Agent Mode: Prompt eingeben
         # → "Start drift autopilot session and fix all critical findings.
         #    After each task, collect audit data. At the end, write
         #    drift-audit.json and show git diff --stat before committing."
```

**Erwartetes Ergebnis:** VS Code öffnet sich, MCP-Server ist via mcp.json konfiguriert.

---

## Phase 1 — Autopilot-Scan (T+02:30 bis T+05:00)

```
T+02:30  # Agent ruft auf:
         drift_session_start(path=".", autopilot=true, ttl_seconds=3600)
         # → session_id: "a1b2c3d4-..."
         # → autopilot.drift_score: 0.497
         # → autopilot.task_count: 10
         # → autopilot.top_signals: [{AVS: 5}, {MDS: 3}, {PFS: 2}]

T+03:00  # Agent zeigt Zusammenfassung:
         # "Found 10 high-priority issues across 3 signals (AVS, MDS, PFS).
         #  Starting fix loop..."
```

**Erwartetes Ergebnis:** 10 priorisierte Tasks, Score 0.497.

---

## Phase 2 — Fix-Loop (T+05:00 bis T+23:00)

### Task 1: AVS — manager.ts (T+05:00)

```
T+05:00  drift_task_claim(session_id, agent_id="copilot")
         # → task: AVS-865008fb, severity: high
         # → "Decouple manager.ts from unstable manager.core.ts"

T+05:30  # Agent editiert src/acp/control-plane/manager.ts
         # (Interface inversion: Import durch Interface-Typ ersetzen)

T+06:30  drift_nudge(session_id, changed_files="src/acp/control-plane/manager.ts")
         # → direction: "improving", delta: -0.032

T+07:00  drift_task_complete(session_id, "copilot", "AVS-865008fb")
         # → tasks_remaining: 9
```

### Task 2: AVS — session-binding-service.ts (T+07:00)

```
T+07:00  drift_task_claim(session_id, agent_id="copilot")
         # → task: AVS-3bfbc2e9, severity: high

T+07:30  # Agent editiert src/infra/outbound/session-binding-service.ts

T+08:30  drift_nudge(session_id, changed_files="src/infra/outbound/session-binding-service.ts")
         # → direction: "improving", delta: -0.028

T+09:00  drift_task_complete(session_id, "copilot", "AVS-3bfbc2e9")
         # → tasks_remaining: 8
```

### Tasks 3-7: AVS + PFS (T+09:00 bis T+17:00, je ~2 min)

```
T+09:00  # Task 3: AVS — service.ts ↔ schtasks.ts
T+11:00  # Task 4: AVS — failover-error.ts ↔ errors.ts
T+13:00  # Task 5: AVS — exec-approvals.ts ↔ exec-approvals-allowlist.ts
T+15:00  # Task 6: PFS — Error-handling pattern consolidation (batch, 3 files)
T+17:00  # Task 7: PFS — Config parsing patterns (batch, 2 files)
```

### Tasks 8-10: MDS Batch (T+17:00 bis T+22:00)

```
T+17:00  drift_task_claim(session_id, agent_id="copilot")
         # → task: MDS-batch-01, batch_eligible: true
         # → affected_files_for_pattern: [12 files with asObjectRecord/trimMaybeString]

T+17:30  # Agent erstellt src/utils/type-guards.ts (shared utility)
         # Agent entfernt Duplikate aus 12 Dateien, ersetzt durch Import

T+20:00  drift_nudge(session_id, changed_files="src/utils/type-guards.ts,extensions/...")
         # → direction: "improving", delta: -0.045

T+20:30  drift_task_complete(session_id, "copilot", "MDS-batch-01")
         # → tasks_remaining: 2

T+21:00  # Task 9: MDS — weitere Duplikat-Gruppe
T+22:00  # Task 10: MDS — letzte Duplikat-Gruppe

T+23:00  drift_task_claim(session_id, agent_id="copilot")
         # → status: "no_tasks_available"
         # → "All 10 tasks completed."
```

---

## Phase 3 — Verifikation (T+23:00 bis T+25:00)

```
T+23:00  drift_diff(session_id, uncommitted=true)
         # → accept_change: true
         # → new_findings: 0
         # → score_delta: -0.187

T+24:00  git diff --stat
         # → 18 files changed, 256 insertions(+), 312 deletions(-)

T+24:30  # Agent zeigt: "All changes verified. No new findings.
         #  Score improved from 0.497 to 0.310 (-37.6%)."
```

---

## Phase 4 — Audit-Export (T+25:00 bis T+28:00)

```
T+25:00  drift_session_end(session_id)
         # → duration_seconds: 1654
         # → score_start: 0.497, score_end: 0.310, score_delta: -0.187
         # → orchestration_metrics: { tasks_completed: 10, nudge_improving: 8, ... }

T+26:00  # Agent schreibt drift-audit.json
         # (Assembliert aus: session_end + collected per-task data + diff verification)

T+27:00  # Agent zeigt zusammenfassung:
         # "Audit trail written to drift-audit.json.
         #  10/10 tasks fixed. Score: 0.497 → 0.310 (-37.6%). Duration: 27:34.
         #  Ready for commit — review diffs above."

T+28:00  # User reviewed, approves:
         git add -A
         git commit -m "fix: resolve 10 drift findings (MCP autopilot demo)"
```

---

## Zusammenfassung

| Metrik | Wert | Quelle |
|--------|------|--------|
| Findings identifiziert | 10 | `findings_summary.total_identified` |
| Findings behoben | 10 | `findings_summary.total_fixed` |
| Score vorher | 0.497 | `demo_run.score_before` |
| Score nachher | 0.310 | `demo_run.score_after` |
| Score-Verbesserung | -37.6% | `demo_run.score_delta` |
| Gesamtdauer | 27:34 min | `demo_run.duration_seconds` |
| Dateien geändert | 18 | `orchestration_metrics.changed_files_total` |
| Drift-Tool-Anteil | 15.2% | `demo_run.tool_time_pct` |
