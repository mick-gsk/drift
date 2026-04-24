---
name: "Drift – Findings Reduzieren (Field-Test)"
agent: agent
description: "Installiert die neuste drift-analyzer-Version, klont ein Ziel-Repository via URL und reduziert Findings maximal via Session-Autopilot, Batch-vor-Einzel-Loop, drift_steer und nudge. Drift-Eigenprobleme werden reproduzierbar als Issues an mick-gsk/drift gemeldet."
---

# Drift – Findings Reduzieren

Du installierst die neuste `drift-analyzer`-Version, analysierst ein externes Repository und behebst darin so viele Drift-Findings wie möglich, ohne Policy-, Signal- oder Architekturentscheidungen des Ziel-Repos zu verändern.

Ziel ist maximale Produktivität: zuerst Batch-fähige Tasks (`batch_eligible=true`) bearbeiten, danach Einzel-Tasks, mit `nudge` nach jeder Änderung und abschließender `diff`-Verifikation.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen:

### Drift Policy Gate (vor Ausführung ausfüllen)

```
- Aufgabe: Neuste drift-Version installieren + Findings im Ziel-Repo maximal reduzieren (Batch vor Einzel)
- Zulassungskriterium erfüllt: [JA / NEIN] → Handlungsfähigkeit (Findings sind sichtbar und adressierbar)
- Ausschlusskriterium ausgelöst: [JA / NEIN] → [falls JA: welches]
- Roadmap-Phase: 1 — blockiert durch höhere Phase: NEIN
- Betrifft Signal/Architektur (§18): NEIN
- Entscheidung: [ZULÄSSIG / ABBRUCH]
- Begründung: [ein Satz]
```

Bei ABBRUCH: keine Ausführung.

## Eingaben

| Parameter   | Beschreibung                                      | Beispiel                                   |
|-------------|---------------------------------------------------|--------------------------------------------|
| `REPO_URL`  | Git-URL des zu analysierenden Repositories        | `https://github.com/mick-gsk/drift.git`    |
| `SCOPE`     | (optional) Scope für Session/Analyse              | `src/` oder `.` für das gesamte Repo       |
| `MAX_TASKS` | Maximale Anzahl Einzel-Tasks pro Durchlauf        | `10` (Default)                             |
| `MAX_BATCH_GROUPS` | Maximale Anzahl Batch-Gruppen pro Durchlauf | `3` (Default)                              |

## Relevante Referenzen

- **Konventionen:** `.github/prompts/_partials/konventionen.md`
- **Issue-Filing (extern):** `.github/prompts/_partials/issue-filing-external.md`
- **Fix-Loop:** `.github/prompts/drift-fix-loop.prompt.md`
- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Skill:** `.github/skills/drift-effective-usage/SKILL.md`

## Scope

- **Analysiert:** Das Ziel-Repository (`REPO_URL`)
- **Verändert:** Nur Quellcode-Muster, die Drift als behebbar ausweist
- **Verändert NICHT:** Policy-, Config-, Architektur- oder Testlogik des Ziel-Repos
- **Issues gehen an:** `mick-gsk/drift` — nicht ans Ziel-Repo

## Ziel

Reduziere die Gesamtzahl der Drift-Findings im Ziel-Repository durch iterative, verifikationsgesicherte Korrekturen. Jede Änderung muss per `nudge` bestätigt und abschließend per `drift_diff` verifiziert werden.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn:

- Die neuste `drift-analyzer`-Version installiert und in `prerequisites.md` dokumentiert ist
- Eine Session mit `session_start(autopilot=true)` im gewünschten `SCOPE` gestartet und dokumentiert ist
- Batch-Gruppen (bis `MAX_BATCH_GROUPS`) vor Einzel-Tasks verarbeitet wurden
- Verbleibende Einzel-Tasks (bis `MAX_TASKS`) verarbeitet wurden
- Jede Änderung durch `nudge` als `improving` oder `stable` bestätigt ist
- `drift_diff(uncommitted=True)` 0 neue Findings zeigt
- Die Session mit `drift_session_end` sauber abgeschlossen wurde
- Alle Artefakte unter `work_artifacts/reduce_findings_<YYYY-MM-DD>/` abgelegt sind
- `issues_filed.md` vorhanden ist (auch wenn keine Issues angelegt wurden)

## Arbeitsregeln

1. **Versions-Freshness zuerst.** Vor jeder Analyse muss die neuste PyPI-Version installiert sein (siehe Phase 0).
2. **Batch vor Einzel.** Zuerst Batch-Gruppen bearbeiten, dann Einzel-Tasks.
3. **`nudge` nach jeder Dateiänderung.** Kein Commit ohne vorheriges `nudge`-Feedback.
4. **Bei `direction=degrading` sofort rückgängig machen.** Nicht durchdrücken, sondern anders lösen.
5. **Keine Policy- oder Signalentscheidungen.** Nur kodierbare Muster beheben, keine Architekturweichen stellen.
6. **Abbruchbedingung:** Bei 3 aufeinanderfolgenden `degrading`-Ergebnissen im selben Loop abbrechen und dokumentieren.
7. **Issue-Filing nur reproduzierbar.** Drift-Bugs nur melden, wenn das Verhalten reproduzierbar und nicht durch fehlerhafte Umsetzung des Fixes erklärbar ist.

## Artefakte

Alle Artefakte unter `work_artifacts/reduce_findings_<YYYY-MM-DD>/`:

1. `prerequisites.md` — installierte Version, Python-Env, Git-Version
2. `session_start_result.json` — vollständige `drift_session_start`-Antwort (Scan + Plan)
3. `constraints.md` — optionale Anti-Pattern-/Negativkontext-Notizen für den Lauf
4. `batch_log.md` — pro Batch-Gruppe: Signal, Dateien, Änderungen, `nudge`-Ergebnisse
5. `fix_log.md` — pro Einzel-Task: Finding, Änderung, `nudge`-Ergebnis
6. `diff_verification.json` — `drift_diff(uncommitted=True)` Ausgabe
7. `session_summary.json` — Ausgabe von `drift_session_end`
8. `issues_filed.md` — angelegte Issues (oder Vermerk "keine Issues")
9. `reduce_findings_report.md` — Zusammenfassung: Ausgangszahl → Endzahl, offene Tasks, Empfehlungen für Drift

---

## Workflow

### Phase 0: Voraussetzungen und Versions-Freshness

**Neuste drift-analyzer-Version installieren:**

```bash
pip install --upgrade drift-analyzer
drift --version
pip index versions drift-analyzer 2>/dev/null | head -1
```

Installierte Version und verfügbare PyPI-Version in `prerequisites.md` dokumentieren.

Falls `pip install --upgrade` scheitert:
- Fehler in `prerequisites.md` protokollieren
- Tatsächlich verwendete Version explizit ausweisen
- Weiterarbeiten mit installierter Version, Einschränkung im Report vermerken

**Repo klonen:**

```bash
git clone <REPO_URL> target_repo
cd target_repo
```

Falls der Klon scheitert (Netzwerk, Auth): Abbruch mit Fehlerdokumentation in `prerequisites.md`.

**Python-Version und Git prüfen:**

```bash
python --version
git --version
```

Beide Werte in `prerequisites.md` festhalten.

---

### Phase 1: Basis-Scan mit Autopilot-Session

```
drift_session_start(
    path=".",
    scope="<SCOPE>",
    autopilot=true
)
```

Dieser Aufruf führt automatisch `validate → brief → scan → fix_plan` durch.

Falls `drift_session_start` fehlschlägt: Fehler in `prerequisites.md` dokumentieren und den Workflow abbrechen.

**Merke:** `session_id` aus der Antwort — sie wird an **jeden** weiteren Tool-Aufruf übergeben.

Session-Ausgabe in `session_start_result.json` ablegen und daraus dokumentieren:
- Gesamtanzahl Findings
- Findings pro Signal-Typ
- Top-5 betroffene Dateien

Optional für bessere Edit-Sicherheit:

```
drift_negative_context(...)
```

Wenn verwendet: zentrale Anti-Pattern in `constraints.md` übernehmen und bei jeder Änderung mitprüfen.

---

### Phase 2: Batch-Loop (bis `MAX_BATCH_GROUPS` oder keine Batch-Gruppe mehr)

Batch-Loop hat Vorrang, um mit einem wiederverwendbaren Fix-Muster mehrere Findings gleichzeitig zu reduzieren.

#### 2a — Aktuellen Plan ziehen und Batch-Gruppe wählen

```
drift_fix_plan(session_id=<session_id>, max_tasks=25)
```

Aus dem aktuellen Plan die nächste unbearbeitete Gruppe mit `batch_eligible=true` wählen.

#### 2b — Gruppe umsetzen

Das gleiche Fix-Muster auf alle `affected_files_for_pattern` anwenden.

Wenn ein neues Symbol eingeführt wird: `drift_steer` pro betroffenem Modul/Dateikontext aufrufen (nicht nur für die erste Datei) und das dominante Pattern übernehmen.

Nach jeder Dateiänderung:

```
drift_nudge(
    session_id=<session_id>,
    changed_files="<pfad/zur/datei.py>"
)
```

Auswertung:
- `improving` oder `stable`: weiter
- `degrading`: Datei-Änderung revertieren, im `batch_log.md` als übersprungen markieren
- 3 aufeinanderfolgende `degrading` in derselben Batch-Gruppe: Gruppe abbrechen

Oscillation-Regel (auch im Batch-Loop):
- Wenn ein CXS-Fix erkennbar EDS-Regression triggert, die Extraktionsstrategie verwerfen und Alternative verwenden.

#### 2c — Batch-Gruppe protokollieren

`batch_log.md` pro Gruppe mit: Signal, Anzahl Zieldateien, erfolgreich/übersprungen, Grund.

---

### Phase 3: Einzel-Loop (bis `MAX_TASKS` oder Abbruchbedingung)

#### 3a — Nächsten Task holen

```
drift_fix_plan(session_id=<session_id>, max_tasks=1)
```

Nur Einzel-Tasks verarbeiten (Batch-Gruppen aus Phase 2 nicht erneut abarbeiten).

Task analysieren: Datei, Signal-Typ, empfohlene Änderung.

#### 3b — Änderung umsetzen

Wenn ein neues Symbol eingeführt wird: vor dem Edit `drift_steer` aufrufen.

Nur die empfohlene Korrektur vornehmen. Keine weiteren Änderungen an der Datei.

#### 3c — nudge nach Änderung

```
drift_nudge(
    session_id=<session_id>,
    changed_files="<pfad/zur/datei.py>"
)
```

Auswertung:
- `direction=improving` oder `stable` → weiter mit 3d
- `direction=degrading` → Änderung rückgängig machen, in `fix_log.md` als "rückgängig" markieren, nächsten Task holen
- 3 × `degrading` in Folge → Abbruchbedingung auslösen

#### 3d — In fix_log.md dokumentieren

```markdown
## Task <N>
- Finding: <Beschreibung>
- Datei: <Pfad>
- Signal: <Signal-Typ>
- Änderung: <Kurzbeschreibung>
- nudge-Ergebnis: improving / stable / degrading
- Aktion: umgesetzt / rückgängig gemacht
```

Phase 3 wiederholen bis `MAX_TASKS` erreicht oder Abbruchbedingung.

---

### Phase 4: Abschluss-Verifikation + Session-Ende

```
drift_diff(session_id=<session_id>, uncommitted=True)
```

Ausgabe in `diff_verification.json` ablegen.

**Kriterium:** 0 neue Findings. Falls neue Findings aufgetreten sind: deren Ursache in `reduce_findings_report.md` erklären.

Dann Session sauber beenden:

```
drift_session_end(session_id=<session_id>)
```

Ausgabe in `session_summary.json` ablegen.

---

### Phase 5: Issue-Filing (nur bei reproduzierbaren Drift-Eigenproblemen)

Issue an `mick-gsk/drift` anlegen, wenn eine der folgenden Bedingungen erfüllt ist:
- reproduzierbarer False Positive
- reproduzierbarer CLI-Fehler/Traceback
- reproduzierbar irreführende `reason`/`next_action`-Texte
- reproduzierbar unbrauchbare Batch-Empfehlung

Wichtig:
- Vor Filing prüfen, ob die eigene Umsetzung korrekt und minimal war
- Bei Unsicherheit Fix sauber wiederholen; erst dann melden
- Deduplizierung gegen bestehende Issues durchführen
- Template aus `.github/prompts/_partials/issue-filing-external.md` verwenden

`issues_filed.md` immer schreiben:
- bei Issues: Titel + URL + Kategorie
- ohne Issues: "Keine reproduzierbaren Drift-Eigenprobleme erkannt"

---

### Phase 6: Report schreiben

`reduce_findings_report.md` mit mindestens diesen Abschnitten:

```markdown
## Versions-Freshness
- drift-analyzer: <Version>
- Python: <Version>
- Datum: <YYYY-MM-DD>

## Ergebnis
- Findings vorher: <N>
- Findings nachher: <N>
- Reduzierung: <N> (–<X>%)

## Batch-Ergebnis
[Tabelle: Gruppe / Signal / Dateien / umgesetzt / übersprungen]

## Bearbeitete Tasks
[Tabelle: Task / Signal / Datei / Ergebnis]

## Offene Tasks
[Liste der nicht bearbeiteten Findings mit Begründung]

## Drift-Tool-Empfehlungen
[Konkrete Empfehlungen ausschließlich für drift selbst]
```

**Nicht ans Ziel-Repo posten.**
