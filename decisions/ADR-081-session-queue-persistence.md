---
id: ADR-081
status: proposed
date: 2026-04-21
supersedes:
---

# ADR-081: Session-Queue-Persistenz via Append-Log

## Kontext

Fix-Plans und Task-Fortschritte liegen ausschließlich im `SessionManager` im RAM (ADR-022). Bei MCP-Server-Neustart, TTL-Ablauf (30 min) oder Agent-Crash geht der Queue-State verloren. Jede neue Agent-Session muss `drift_fix_plan` erneut aufrufen und begrifft die bisher erledigten Tasks nicht. Das führt zu **Ad-hoc-Fixes ohne Cross-Session-Kontinuität**: wiederholte Mikro-Patches statt kohärenter Batch-Arbeit, weil die priorisierte Reihenfolge bei jedem Restart verloren geht.

`SessionManager.save_to_disk()` / `load_from_disk()` existieren als vollständiger Snapshot, werden aber nur manuell aufgerufen und halten transienten Laufzeit-State (Leases, Metriken, Trace) fest — was bei Restart falsche Informationen reaktiviert.

## Entscheidung

**Einführen eines append-only Event-Logs `<repo>/.drift-cache/queue.jsonl`**, das ausschließlich Queue-Mutationen persistiert:

- `plan_created` → vollständige Task-Liste (Snapshot bei jedem `drift_fix_plan`)
- `task_claimed` → `{task_id, agent_id}` (transient, wird beim Replay ignoriert)
- `task_released` → `{task_id, reclaim_count}` (transient, ignoriert)
- `task_completed` → `{task_id}` (terminal, wirkt durch Replay fort)
- `task_failed` → `{task_id}` (terminal, wirkt durch Replay fort)

`drift_session_start` replayt den Log standardmäßig und rekonstruiert `selected_tasks`, `completed_task_ids`, `failed_task_ids` aus dem jüngsten `plan_created` + allen darauf folgenden terminalen Events. Ein neuer Parameter `fresh_start: bool = False` erlaubt es Agenten/Tests, diesen Replay zu überspringen.

**Explizit nicht Teil der Entscheidung**:

- Leases und Metriken werden beim Replay nicht wiederhergestellt (abgelaufene Leases würden neue Claims blockieren, Metriken sind per-Session).
- Keine Multi-Prozess-Koordination: ein Writer pro Repo-Arbeitskopie; OS-Lock nur als Best-Effort-Absicherung gegen versehentliche parallele Schreiber.
- Der bestehende Snapshot-Pfad `save_to_disk`/`load_from_disk` bleibt unverändert und dient Debug/Export.

## Begründung

Append-Log statt Snapshot wurde gewählt, weil:

1. **Atomische Append-Semantik** auf den üblichen Dateisystemen verhindert Lost-Update-Konflikte bei parallelen Task-Mutationen innerhalb eines Prozesses.
2. **Audit-Trail**: Events sind chronologisch und nicht destruktiv; eine Rotation kompaktiert (verwirft nur noch transiente Events), verfälscht aber keine terminalen Entscheidungen.
3. **Forward-Compatibility**: jedes Event trägt ein `v`-Feld und unbekannte `type`-Werte werden beim Replay übersprungen, sodass zukünftige Event-Typen (z. B. `task_dismissed`, `plan_invalidated`) rückwärtskompatibel hinzugefügt werden können.
4. **Robustheit**: korrupte Einzelzeilen werden beim Replay geloggt und übersprungen, nicht als Fatal-Error behandelt.

Alternative "Full-Snapshot pro Mutation" wurde verworfen, weil sie bei großen Task-Listen teuer ist, Race-Conditions bei parallelen Writern verschärft und keinen Audit-Trail liefert.

Framing als `fix:` (Adoption-Blocker für MCP-Fix-Loop) statt `feat:` wurde begründet durch Policy §8 Einführbarkeit: Ad-hoc-Fix-Chaos zwischen Sessions verhindert, dass agentische Nutzung empirisch nachgewiesen werden kann — ein direkter Blocker für die Distribution-Phase.

## Konsequenzen

**Positive**:

- Cross-Session-Queue-Kontinuität: Agent kann nach Editor-Neustart weiterarbeiten, ohne Fortschritt zu verlieren.
- Deterministisches Replay: identische Event-Reihenfolge → identischer rekonstruierter State.
- Kein neuer MCP-Tool-Name; nur ein neuer optionaler Parameter `fresh_start` auf `drift_session_start`.

**Negative / Trade-offs**:

- Ein weiterer Pfad, den Tests gegen Seiteneffekte isolieren müssen (`tmp_path`).
- `.drift-cache/queue.jsonl` kann in langlebigen Repos wachsen; Rotation bei 10 MB mindert, entfernt das Problem aber nicht vollständig.
- Best-Effort-Lock schützt nicht gegen bösartige Manipulation der Logdatei (Policy §18 STRIDE: Tampering — siehe audit_results-Aktualisierung).
- Replay rekonstruiert keinen lease/metric-State; wiederaufnahmepunkt ist bewusst "Plan + Abschlüsse", nicht "exakter Laufzeitzustand".

**Auswirkungen auf bestehende ADRs**:

- ADR-022 (Sessions): erweitert um persistierenden Queue-State auf Plan/Task-Ebene.
- ADR-025 (Task-Queue-Leasing, proposed): bleibt orthogonal — Leases bleiben transient.

## Validierung

- Unit-Tests in `tests/test_session_queue_log.py` belegen: Roundtrip, korrupte-Zeilen-Toleranz, Thread-Safety, Rotation-Kompaktierung, UTF-8-Korrektheit auf Windows.
- Integration-Tests in `tests/test_session.py::TestRestartReplay` belegen: Replay nach simuliertem Neustart, Opt-Out via `fresh_start=true`, Write-Hooks in `claim_task`/`complete_task`/`release_task`.
- Evidenz: `benchmark_results/v2.27.0_feature_evidence.json` dokumentiert Roundtrip-Verhalten und Replay-Korrektheit.
- Policy §18: FMEA-, STRIDE- und Risk-Register-Einträge zu Queue-Log-Korruption, Tampering und Replay-Inkonsistenz.
- Lernzyklus-Ergebnis nach Distribution-Phase: **zurückgestellt** — bestätigt oder widerlegt anhand empirischer Nutzungsdaten agentischer Sessions.
