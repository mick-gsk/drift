# Erkenntnisse: mattpocock/ai-engineer-workshop-2026-project

> Quelle: https://github.com/mattpocock/ai-engineer-workshop-2026-project
> Analysiert: 2026-04-30
> Kontext: AI Engineer Workshop von Matt Pocock — Hands-on-Sandbox für autonome Coding-Agenten

---

## Projekt-Überblick

**Cadence** — eine Mini-Udemy-Plattform (React Router v7 · TypeScript · SQLite + Drizzle ORM · Tailwind/shadcn · Vitest).

Ausgangspunkt ist ein `client-brief.md` (fiktive Slack-Nachricht einer VP Product), die Gamification-Features fordert (Punkte, Levels, Streaks, Quiz-Incentives). Die Teilnehmer sollen diesen Brief mit Coding-Agenten von Brief → PRD → Issues → Implementierung umsetzen.

---

## AFK-Agent-Workflow: `ralph/`

Das Herzstück des Repos ist der `ralph/`-Ordner — ein vollständiger, produktionstauglicher AFK-Agent-Loop.

### Dateien

```
ralph/
  prompt.md    ← System-Prompt für den Loop-Agenten
  once.sh      ← Einmaliger Lauf (development)
  afk.sh       ← Loop-Modus: N Iterationen, docker sandbox
```

### `once.sh` — Einfacher Einzellauf

```bash
claude --permission-mode acceptEdits \
  "Previous commits: $commits  Issues: $issues  $prompt"
```

- Liest offene Issues aus `issues/*.md`
- Liest letzte 5 Commits als Kontext
- Gibt alles an Claude mit `--permission-mode acceptEdits` (keine Bestätigungsdialoge)

### `afk.sh` — Echter AFK-Loop

```bash
for ((i=1; i<=$1; i++)); do
  docker sandbox run claude . -- \
    --verbose --print --output-format stream-json \
    "Previous commits: $commits  Issues: $issues  $prompt" \
  | jq -rj "$stream_text"

  if [[ "$result" == *"<promise>NO MORE TASKS</promise>"* ]]; then
    echo "Ralph complete after $i iterations."
    exit 0
  fi
done
```

- Claude läuft isoliert in **Docker Sandbox** (kein Host-Filesystem-Zugriff außerhalb des Projekts)
- Output-Format `stream-json` + `jq`-Streaming für Live-Ausgabe
- **Stop-Condition:** Claude gibt `<promise>NO MORE TASKS</promise>` aus → Loop bricht ab

### `ralph/prompt.md` — Agentensteuerung

Klare Prioritätsreihenfolge für den Agenten:
1. Critical bugfixes
2. Development infrastructure (Tests, Types, Dev-Scripts) — **Precursor vor Features**
3. Tracer bullets für neue Features (dünne End-to-End-Slices zuerst)
4. Polish und Quick Wins
5. Refactors

Pflicht vor Commit: `npm run test` + `npm run typecheck`  
Pflicht nach Commit: Issue nach `issues/done/` verschieben oder Note anhängen

---

## Erkenntnisse

### 1. `<promise>`-Tag als Stop-Condition

**Insight:** Der Agent signalisiert "keine Aufgaben mehr" durch ein strukturiertes XML-Tag im Text-Output — kein separates API-Signal, kein Exit-Code. Das Shell-Skript greift das mit `grep` heraus.

**Übertragbarkeit für Drift:** Drift's `drift_session_end` nutzt ähnliche Konventionen für Handover-Artefakte. Für AFK-Loop-Szenarien wäre ein analoges Output-Tag (`<drift:done>` o.ä.) eine robuste Stop-Condition für externe Orchestratoren.

---

### 2. Docker Sandbox für Agent-Isolation

**Insight:** `docker sandbox run claude .` gibt dem Agenten Zugriff auf das Projektverzeichnis, aber isoliert ihn vom Host. Das verhindert ungewollte Seiteneffekte (keine SSH-Keys, keine globalen Configs, keine anderen Projekte).

**Übertragbarkeit für Drift:** Für Field-Tests gegen externe Repositories ist Docker-Sandboxing das korrekte Sicherheitsmodell. Kein `pip install drift-analyzer` mit Host-Seiteneffekten.

---

### 3. Issues-als-Dateien (kein GitHub)

**Insight:** Lokale `.md`-Dateien in `issues/` statt GitHub-Issues. Agent liest per `cat issues/*.md`, bearbeitet eine Task, verschiebt sie nach `issues/done/`. Kein GitHub-Token erforderlich, vollständig offline, keine Race Conditions.

**Muster:**
```
issues/
  001-add-points-schema.md    ← offen
  002-streak-tracking.md      ← offen
  done/
    000-fix-login-bug.md      ← erledigt
```

**Übertragbarkeit für Drift:** Das Muster "lokale Issue-Dateien als Agentengedächtnis" ist deutlich robuster als GitHub-Issues für autonome Loops. Drift-Backlog-Items (`master-backlog/`) folgen einem ähnlichen Prinzip.

---

### 4. AFK vs. HITL — Explizite Kategorisierung

**Insight:** Issues werden beim Erstellen explizit als **AFK** (autonom ausführbar) oder **HITL** (Human In The Loop, braucht Entscheidung) kategorisiert. Der `ralph`-Prompt bearbeitet nur AFK-Issues.

**HITL-Beispiele:** Architekturentscheidungen, Design-Reviews, ambige Anforderungen
**AFK-Beispiele:** Schema-Migrations schreiben, Service-Tests ergänzen, UI-Komponenten implementieren

**Übertragbarkeit für Drift:** In Drift's `POLICY.md` gibt es das Konzept "erfordert Maintainer-Approval" vs. "eigenständig". Die AFK/HITL-Dichotomie ist eine schärfere, direkt agenten-operationalisierbare Formulierung desselben Konzepts.

---

### 5. Vertikale Slices (Tracer Bullets) statt horizontales Slicing

**Insight:** Der `tdd`-Skill enthält eine explizite Anti-Pattern-Warnung:

```
WRONG (horizontal):
  RED:   test1, test2, test3, test4, test5
  GREEN: impl1, impl2, impl3, impl4, impl5

RIGHT (vertical / tracer bullets):
  RED→GREEN: test1→impl1
  RED→GREEN: test2→impl2
  ...
```

Horizontal geschriebene Tests testen "imaginiertes" Verhalten, nicht reales. Vertikale Slices erzwingen, dass jeder Test auf echtem, gerade implementiertem Code basiert.

**Übertragbarkeit für Drift:** Beim Entwickeln neuer Signale: Nicht erst alle TP/TN-Fixtures schreiben, dann implementieren. Lieber: eine Fixture → Signal-Logik → nächste Fixture. Das `drift-ground-truth-fixture-development`-Skill sollte diese Warnung explizit enthalten.

---

### 6. Commit-Nachrichten als Agentengedächtnis

**Insight:** Der `ralph`-Prompt schreibt vor, dass Commit-Nachrichten enthalten müssen:
1. Key decisions made
2. Files changed
3. Blockers or notes for next iteration

Der nächste Agent-Loop-Durchlauf liest die letzten 5 Commits als Kontext. **Git-History ersetzt persistente Agentenmemorys.**

**Übertragbarkeit für Drift:** Drift's Conventional-Commit-Pflicht erfüllt das teilweise. Für AFK-Loops wäre ein strukturierterer Commit-Footer (z.B. `Blockers: ...`) wertvoller als freier Text.

---

### 7. Deep Modules als Testbarkeits-Prinzip

**Insight:** Der `improve-codebase-architecture`-Skill und der `tdd`-Skill bauen beide auf John Ousterhouts "Deep Module"-Konzept auf: **kleine Interface, große Implementation**. Flache Module (Interface-Komplexität ≈ Implementierungs-Komplexität) sind schwer testbar, weil man immer interne Details mocken muss.

**Direkte Umsetzung im Repo:**
- `app/test/setup.ts` erstellt eine echte In-Memory-SQLite-DB mit echten Drizzle-Migrations — kein Schema-Mock.
- Tests mocken nur den `~/db`-Export via `vi.mock`, nicht die Datenbankstruktur.
- Ergebnis: Tests überleben vollständige Refaktors der Service-Internals.

**Übertragbarkeit für Drift:** Drift-Signale sind bereits als tiefe Module konzipiert (BaseSignal-Interface + komplexe Heuristik darunter). Tests sollten an den Signal-Outputs ansetzen, nicht an internen Scoring-Zwischenwerten.

---

### 8. `--permission-mode acceptEdits`

**Insight:** Claude CLI Flag, das automatische Datei-Edits ohne Bestätigung erlaubt — das direkte Äquivalent zu `DRIFT_SKIP_HOOKS=1` für aggressive AFK-Szenarien. Ohne dieses Flag blockiert jeder `write_file`-Aufruf auf Benutzereingabe.

---

### 9. PRD → Issues → Implementierung als vollständiger Workflow

**Skill-Kette:**
1. `write-a-prd` — Client-Brief → strukturiertes PRD mit User Stories + Implementation Decisions
2. `prd-to-issues` — PRD → atomare, vertikal geslicte Issue-Dateien
3. `ralph`-Loop — Issues → Implementierung (AFK-only)

**Interessant:** Der PRD-Skill beinhaltet explizit ein "relentless interview" (Sokratisches Design-Gespräch) bevor irgendwas implementiert wird. Der `grill-me`-Skill macht das als separaten wiederverwendbaren Workflow.

---

## Skills-Übersicht

| Skill | Zweck | Besonderheit |
|---|---|---|
| `tdd` | Red-Green-Refactor mit Tracer Bullets | Explizite Anti-Pattern-Warnung gegen horizontales Slicing |
| `write-a-prd` | Client-Brief → PRD | Relentless Interview vor Implementierung |
| `prd-to-issues` | PRD → atomare Issue-Dateien | AFK/HITL-Kategorisierung, Dependency-Tracking |
| `improve-codebase-architecture` | Deep-Module-Refactoring | 3+ Parallel-Subagents für Interface-Designs |
| `grill-me` | Socratisches Design-Interview | Fragen einzeln, mit eigener Empfehlung pro Frage |
| `better-sqlite3-rebuild` | Fix native Node-Module | Proaktiv `npm rebuild` ohne Rückfrage |

---

## See Also

- `.github/skills/drift-signal-development-full-lifecycle/SKILL.md` — Ähnliches Lifecycle-Konzept für Drift-Signale
- `.github/skills/subagent-driven-development/SKILL.md` — Ähnliches Parallel-Subagent-Pattern wie `improve-codebase-architecture`
- `POLICY.md` §16 — Maintainer-Approval-Grenze (entspricht HITL-Kategorisierung)
- `.learnings/LEARNINGS.md` — Hauptdatei für alle Learnings
