---
name: workspace-automation-orchestrator
description: "Erkennt wiederkehrende manuelle Entwicklungsprozesse im Workspace, priorisiert sie nach ROI und fuehrt sichere lokale Automationen automatisch aus. IMMER verwenden, wenn der User repetitive manuelle Schritte, Produktivitaetsverluste, wiederholte QA/Gate-Ablaufe oder den Wunsch nach weniger manuellem Agent-Anstossen beschreibt. Keywords: automate workspace, repetitive tasks, auto run, quality gates, drift workflow automation, productivity."
---

# Workspace Automation Orchestrator

Dieser Skill reduziert wiederholte manuelle Ausfuehrungsschritte, indem er Prozesse erkennt und innerhalb klarer Safe-Scopes automatisch orchestriert.

## Referenzen laden

Lade bei Bedarf die folgenden Dateien fuer Details:

- `references/contracts.md` fuer Detection-, Safety- und Execution-Contract
- `references/v1-automations.md` fuer den initialen Automationskatalog
- `references/rollout.md` fuer den kontrollierten Rollout und Monitoring
- `evals/evals.json` fuer die ersten Skill-Evaluationsprompts

## Ziel

- Wiederkehrende manuelle Prozesse im aktuellen Workspace erkennen
- Automationskandidaten nach Nutzen priorisieren
- Sichere lokale Ablaufe automatisch ausfuehren
- Risiko-Aktionen strikt blockieren und sauber eskalieren

## Trigger

Nutze diesen Skill, wenn der User:

- von regelmaessig wiederholten manuellen Schritten berichtet
- Produktivitaet durch wiederholtes manuelles Anstossen verliert
- konsistente Qualitaet/Gate-Compliance erreichen will
- nach "automatisch erkennen", "automatisieren" oder "nicht jedes Mal manuell" fragt

## Betriebsmodus

Dieser Skill arbeitet im Hybrid-Modus:

1. Discovery bei Task-Start
2. ROI-Scoring fuer Kandidaten
3. Automatische Ausfuehrung nur bei erreichtem Schwellwert und nur in Safe-Scopes
4. Sonst Vorschlag + explizite Freigabe

Standardprofil fuer dieses Repo: `balanced`.

Profile:

- `strict`: auto-run nur bei sehr hohem ROI und null Safety-Zweifel
- `balanced`: auto-run bei klarem ROI in der Allowlist
- `aggressive`: nur auf expliziten User-Wunsch, nie als Default

## Safety-Vertrag (nicht verhandelbar)

### Harte Block-Regeln

Folgende Aktionen werden niemals automatisch ausgefuehrt:

- `git push` oder sonstige Remote-Write-Operationen
- automatisches Posten von Issue-/PR-Kommentaren
- destructive Git-Kommandos (`git reset --hard`, `git checkout --`, History-Rewrites)

### Eskalations-Regel

Wenn ein geplanter Schritt nicht in der Allowlist ist:

1. Aktion blockieren
2. Grund nennen
3. sichere Alternative vorschlagen
4. explizite User-Freigabe anfordern

## Detection-Contract

Suche nach Automationskandidaten anhand folgender Signale:

- identische oder stark aehnliche Befehle wiederholen sich
- gleiche Sequenzen erscheinen mehrfach (z. B. test -> gate-check -> audit)
- wiederkehrende Quality- oder Gate-Fehler mit demselben Fix-Pattern
- hoher manueller Koordinationsaufwand bei niedrigem Entscheidungsbedarf

### ROI-Heuristik

Prioritaet fuer Automation:

`priority = frequency_score * effort_score * consistency_gain / risk_factor`

Hinweise:

- `frequency_score`: Wie oft der Ablauf wiederkehrt
- `effort_score`: Zeit-/Kontextkosten pro manueller Ausfuehrung
- `consistency_gain`: Qualitaetsgewinn durch Standardisierung
- `risk_factor`: Ausfuehrungsrisiko (niedriger ist besser)

Auto-Run nur bei:

- Schwellwert erreicht
- Aktion in Safe-Scopes
- keine aktive Block-Regel verletzt

### Schwellwerte (balanced)

- `priority >= 40`: automatisch ausfuehren
- `priority 20-39`: als Vorschlag ausgeben, optional auf Rueckfrage ausfuehren
- `priority < 20`: nicht automatisieren

Zusatzregel:

- Wenn `risk_factor > 1.0`, keine automatische Ausfuehrung; nur Vorschlag mit Begruendung

## Safe-Scopes (V1)

V1 nutzt vorhandene Repo-Kommandos statt neuer Parallel-Logik.

Die autoritative V1-Allowlist und Denylist steht in:

- `references/v1-allowlist.md`

### Erlaubte lokale Orchestrierung

- `make test-fast`
- `make check`
- `make gate-check COMMIT_TYPE=<feat|fix|chore|signal>`
- `make audit-diff`
- `make changelog-entry COMMIT_TYPE=<...> MSG='...'`
- `make catalog`
- gezielte lokale pytest-Laeufe fuer betroffene Tests

### Erlaubte Analyse-/Discovery-Schritte

- Status-/Diff-Pruefung (read-only)
- Erkennen wiederkehrender Task-Sequenzen
- Ableiten naechster lokaler Safe-Aktionen

## Ausfuehrungsprotokoll

1. **Scan**
   - Aktuelle Aufgabe erfassen
   - Wiederholungsmuster im aktuellen Arbeitskontext erkennen
2. **Score**
   - Kandidaten nach ROI-Heuristik priorisieren
3. **Safety-Gate**
   - Jede Kandidatenaktion gegen Hard-Blocks und Allowlist pruefen
4. **Execute or Escalate**
   - In Safe-Scopes: automatisch ausfuehren
   - Ausserhalb: blockieren, begruenden, Freigabe anfordern
5. **Report**
   - Was automatisch ausgefuehrt wurde
   - Was blockiert wurde und warum
   - Empfohlene naechste Schritte

### Reihenfolge fuer V1-Auto-Orchestrierung

Wenn mehrere Aktionen in den Auto-Run fallen, nutze diese Reihenfolge:

1. `make catalog` (Discovery)
2. `make gate-check COMMIT_TYPE=<...>` (fruehe Gate-Sichtbarkeit)
3. `make audit-diff` (nur wenn relevant)
4. `make test-fast` (schnelle Verifikation)

Regel fuer `make check`:

- Nur automatisch starten, wenn User explizit "vollstaendig" oder "full check" verlangt
- Sonst als Vorschlag ausgeben, weil Laufzeit und Umfang hoeher sind

## Output-Vertrag

Der Skill liefert immer einen strukturierten Kurzreport:

- `detected_repetitions`: erkannte wiederkehrende Prozesse
- `auto_executed`: automatisch ausgefuehrte Safe-Aktionen
- `blocked_actions`: blockierte Aktionen inkl. Block-Grund
- `manual_approvals_needed`: Aktionen mit Freigabebedarf
- `next_best_automations`: Top-Kandidaten fuer weitere Automatisierung

Template:

```text
Automation Report
- profile: <strict|balanced|aggressive>
- detected_repetitions:
   - <pattern>: <evidence>
- auto_executed:
   - <command>: <status>
- blocked_actions:
   - <action>: <reason>
- manual_approvals_needed:
   - <action>: <why>
- next_best_automations:
   - <candidate>
```

## Drift-spezifische Integrationsregeln

- Drift Policy Gate weiterhin vor nicht-trivialen Aenderungen beachten
- Existierende Repo-Workflows und Make-Targets bevorzugen
- Keine neue Automationslogik einfuehren, wenn ein bestehender Befehl den Zweck bereits erfuellt
- Bei Unsicherheit konservativ bleiben: nicht ausfuehren, sondern eskalieren

## Beispiele

### Beispiel 1: Wiederkehrende QA-Sequenz

Input-Situation:
- User startet mehrfach pro Tag dieselbe Sequenz aus `test-fast`, `gate-check`, `audit-diff`

Erwartetes Verhalten:
1. Sequenz als wiederkehrenden Prozess erkennen
2. ROI hoch einstufen
3. komplette Sequenz in Safe-Scopes automatisch ausfuehren
4. Ergebnis kompakt reporten

### Beispiel 2: Unsichere Aktion mit Remote-Write

Input-Situation:
- Workflow endet mit vorgeschlagenem `git push`

Erwartetes Verhalten:
1. `git push` blockieren
2. Block-Grund klar nennen
3. nur sichere lokale Vorstufen ausfuehren
4. fuer Push explizite User-Freigabe anfordern

## Grenzen

Dieser Skill automatisiert V1 bewusst nur lokale, risikoarme Workflows.
Er ist kein Freifahrtschein fuer autonome Remote-Aktionen oder Policy-Bypass.
