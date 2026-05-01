# Context-Engineering Contract

> Shared Contract fuer Harness-Prompts, die die Sichtbarkeit, Frische und Repo-Lokalitaet von Agenten-Kontext bewerten.

## Ziel

Context-Engineering ist nur dann stark, wenn ein Agent die relevanten Informationen repo-lokal finden, zeitlich einordnen und fuer den naechsten Schritt verwenden kann.

## Statischer Kontext

Statischer Kontext sind versionierte, repo-lokale Quellen, die auch ohne laufenden Prozess lesbar bleiben.

Erwartete Beispiele:

- Root-Maps wie `AGENTS.md`
- Entwickler-Workflows wie `DEVELOPER.md`
- versionierte Architektur-, Prompt-, Audit- und Contract-Dokumente
- maschinenlesbare Dateien wie Schemas, Tool-Karten oder Manifest-Dateien

Prueffrage: Kann ein spaeterer Agent diese Information ohne Chat-Historie, Slack oder Fremdsysteme im Repository finden?

## Dynamischer Kontext

Dynamischer Kontext sind laufzeit- oder zustandsnahe Signale, die eine aktuelle Arbeitssituation beschreiben.

Erwartete Beispiele:

- Working-Tree-Status, geaenderte Dateien und Diff-Kontext
- letzter relevanter Test-, Check- oder Gate-Status
- CI/CD-Status, sofern repo-lokal oder ueber vorhandene Tools nachvollziehbar
- agent-lesbare Logs, Metriken, Traces oder Repro-Bundles
- Verzeichnis- oder Einstiegsmapping fuer den aktuellen Run

Prueffrage: Kann ein Agent erkennen, wie frisch der Zustand ist und ob er fuer die naechste Entscheidung reicht?

## Single Source Of Truth

Aus Agentensicht existiert nur Wissen, das repo-lokal oder ueber einen klar benannten, legitimen Zugriffspfad erreichbar ist.

- Wissen nur in Chat, Slack, Google Docs oder in Koepfen ist kein verlaesslicher Kontext.
- Wenn externe oder vertrauliche Quellen benoetigt werden, muessen Quelle, Zugriffsbasis und Vertrauensgrad explizit markiert werden.
- Wenn eine Information nicht versioniert oder wiederauffindbar ist, zaehlt sie als Luecke.

## Mindestoutput Fuer Context-Engineering-Audits

Ein spezialisierter Context-Engineering-Prompt sollte mindestens diese Punkte explizit ausgeben oder als Artefakt festhalten:

- welche statischen Quellen den Agenten wirklich tragen
- welche dynamischen Signale aktuell verfuegbar und wie frisch sie sind
- welche entscheidenden Informationen ausserhalb des Repositories liegen
- welcher Hebeldefekt die groesste Kontextluecke schliesst

Reine Beschreibungsprosa ohne Gap-Entscheidung, Frische-Einordnung oder naechsten Hebel erfuellt diesen Vertrag nicht.