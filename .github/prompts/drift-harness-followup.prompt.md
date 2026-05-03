---
name: "drift-harness-followup"
agent: agent
description: "Schaerft einen vorhandenen Harness-Lauf zu einer direkten Folgeumsetzung: liest bestehende Artefakte, waehlt den naechsten offenen Hebeldefekt und setzt genau eine eng validierte Harness-Verbesserung ohne neue Folge-Artefakte um."
---

# Drift Harness Follow-up

Nutze diesen Prompt nach einem Lauf von `drift-harness-engine`, wenn unter `work_artifacts/harness_engine_<YYYY-MM-DD>/` bereits ein Artefaktordner existiert und genau der naechste offene Harness-Defekt umgesetzt werden soll.

Du fuehrst **kein** neues Voll-Audit durch. Du liest nur so viel aus den vorhandenen Artefakten, wie noetig ist, um den naechsten offenen Hebeldefekt zu waehlen, und setzt dann genau **eine** schmale Verbesserung direkt im Repository um.

Der Prompt ist nur erfolgreich, wenn aus Artefaktbefunden eine reale Code-, Script-, Test- oder Contract-Aenderung wird. Neue Folge-Artefakte, neue Backlog-Prosa oder ein zweites Audit zaehlen hier nicht als Fortschritt.

## Was Hier Mit Follow-up Gemeint Ist

Follow-up bedeutet in diesem Prompt:

- einen bereits identifizierten Harness-Defekt aus vorhandenen Artefakten in eine direkte Repo-Aenderung uebersetzen
- die Auswahl auf den naechsten offenen Hebel fokussieren statt die ganze Harness-Landschaft erneut zu vermessen
- den Defekt so schmal bearbeiten, dass ein enger Check die Wirkung oder Widerlegung schnell zeigen kann

Nicht gemeint sind:

- ein neues Voll-Audit der Harness-Engine
- ein weiterer Artefaktlauf unter `work_artifacts/`
- allgemeine Zusammenfassungen oder Strategietexte ohne direkte Umsetzung
- paralleles Abarbeiten mehrerer plausibler Defekte in einem Lauf

Kurztest: Wenn der naechste Schritt nicht in einer direkten Aenderung an Code, Tests, Scripts, Contract-Checks oder einer zwingend betroffenen Kontrollflaeche endet, bist du noch nicht im Follow-up.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- `.github/instructions/drift-policy.instructions.md`
- `.github/prompts/_partials/konventionen.md`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- `DEVELOPER.md`
- `scripts/check_agent_harness_contract.py`
- `tests/test_agent_harness_contract.py`
- `drift-harness-engine.prompt.md`
- `drift-context-engineering.prompt.md`

## Eingabe

Erwarte einen vorhandenen Artefaktordner unter `work_artifacts/harness_engine_<YYYY-MM-DD>/`.

Lies daraus mindestens:

- `harness_engine_report.md`
- `leverage_findings.md`
- `autonomy_ladder.md`
- `validation_log.md`

Ziehe `source_map.md` und `system_model.md` nur dann hinzu, wenn der naechste Defekt ohne sie nicht sauber eingegrenzt werden kann.

Wenn kein Harness-Artefaktordner existiert: stoppe und verweise zuerst auf `drift-harness-engine`.

Wenn mehrere Artefaktordner existieren: verwende standardmaessig den neuesten, ausser der User nennt einen anderen.

Wenn einer der vier Pflichtartefakte fehlt, stoppe nicht stillschweigend. Benenne exakt, welche Datei fehlt, welcher Teil der Defektwahl dadurch unsicher wird und ob trotzdem ein enger Follow-up-Lauf mit reduzierter Sicherheit moeglich ist.

Wenn die Defektwahl daran scheitert, dass der statische oder dynamische Kontext des Repositories selbst unklar, stale oder nur ausserhalb des Repositories vorhanden ist, stoppe die direkte Umsetzung und route zuerst in `drift-context-engineering.prompt.md`.

## Pflichtausgabe Vor Dem Ersten Edit

Bevor du irgendetwas implementierst, gib genau diese vier Punkte aus:

1. verwendeter Artefaktordner
2. ausgewaehlter Defekt mit Defekt-ID oder Kurzname
3. lokale Hypothese, warum genau dieser Defekt der naechste Hebel ist
4. billigster Check, der diese Hypothese falsifizieren kann

Wenn du diese vier Punkte nicht sauber benennen kannst, darfst du noch nicht editieren.

## Ziel

Setze genau **eine** fokussierte Folgeverbesserung um, basierend auf dem hoechsten noch offenen Hebeldefekt aus den Artefakten.

Standard-Priorisierung:

1. offener Defekt mit expliziter Priorisierung im Report oder in `leverage_findings.md`
2. Defekt, der die Autonomieleiter am staerksten blockiert
3. Defekt, der mit dem schmalsten Check am billigsten falsifizierbar ist

Tie-Breaker in dieser Reihenfolge:

1. Defekt, der aus Dokumentation einen maschinellen Vertrag machen kann
2. Defekt, der fehlgeschlagene Agentenlaeufe reproduzierbarer macht
3. Defekt, der die naechste Autonomiestufe freischaltet, ohne neue breite Architekturarbeit zu oeffnen
4. Defekt, der mit bestehenden Dateien und Tests umgesetzt werden kann

Wenn die aktuellen Artefakte dem Stand vom 2026-04-30 entsprechen, ist der Default-Fokus **FU-004: kompakter Repro-Bundle-Pfad fuer fehlgeschlagene Agentenlaeufe**.

Oeffne keinen neuen Defekt, solange ein hoeher priorisierter offener Defekt aus den Artefakten noch nicht bewusst verworfen wurde.

Wenn du vom priorisierten Defekt abweichst, musst du explizit benennen:

- welcher hoehere Defekt verworfen wurde
- wodurch er im aktuellen Lauf blockiert ist
- warum der neue Defekt trotzdem der hoehere unmittelbare Hebel ist

## Konkreter Implementierungsvertrag

- Setze genau **eine** Verbesserungsscheibe um.
- Beruehre nur die Dateien, die den gewaehlten Defekt direkt kontrollieren, plus die kleinste noetige Test- oder Doku-Flaeche.
- Wenn der Defekt mit einem Test, Contract-Check oder maschinenlesbaren Export loesbar ist, bevorzuge das gegenueber reiner Prosa.
- Wenn der erste Eingriff nur Doku aendert, obwohl ein Check oder Script moeglich waere, ist der Ansatz zu schwach und muss geschaerft werden.
- Fuehre keine zweite benachbarte Verbesserung ein, nur weil sie bequem erscheint.
- Erzeuge keine neuen Folge-Artefakte unter `work_artifacts/`, solange der User das nicht ausdruecklich verlangt.
- Wenn mehrere kleine Dateien plausibel sind, bevorzuge die direkt kontrollierende Stelle vor einer neuen Hilfsabstraktion.
- Wenn ein bestehender Check fast den gesuchten Vertrag ausdrueckt, schaerfe ihn statt einen parallelen Mechanismus einzufuehren.

### Architektonische Einschraenkungen

Wenn der gewaehlte Defekt Architekturgrenzen, Modulzustand oder Verantwortungsvermischung betrifft, behandle "guten Code" nicht als Stilziel. Uebersetze ihn in eine mechanische Grenze.

Default-Schichtenmodell fuer solche Harness-Follow-ups:

```text
Types -> Config -> Repo -> Service -> Runtime -> UI
```

Jede Schicht darf nur aus Schichten links von ihr importieren. Eine zulaessige Aenderung benennt deshalb mindestens:

- welche Schicht betroffen ist
- welche Importkante erlaubt, verboten oder noch ungeprueft ist
- welcher Mechanismus die Regel traegt: deterministische Linter, LLM-Auditor, Strukturtests, pre-commit oder CI-Validierung
- welcher schmale Check belegt, dass die Grenze nicht nur dokumentiert, sondern durchsetzbar ist

Wenn keine mechanische Durchsetzung existiert, ist der Follow-up nicht fertig. Der naechste kleinste Schritt ist dann ein Test, Contract-Check, Script oder eine klar maschinenlesbare Regel, nicht ein weiterer Absatz mit Architekturabsicht.

Wenn der gewaehlte Defekt **FU-004** ist, gilt eine Verbesserung nur dann als ausreichend konkret, wenn sie mindestens diese Frage beantwortet: Wie kann ein spaeterer Agent einen fehlgeschlagenen Turn aus einem kompakten repo-lokalen Bundle nachvollziehen, ohne Terminal-Archaeologie oder Chat-Historie zu brauchen?

Ein FU-004-Ansatz ist stark, wenn er moeglichst viele dieser Elemente repo-lokal erfasst:

- kurze Session-Zusammenfassung
- relevanter Fehler- oder Remediation-Kontext
- betroffene Dateien oder Diff-Kontext
- letzter nudge-, diff- oder Check-Status
- ein klarer Einstiegspunkt fuer den naechsten Agenten

Ein FU-004-Ansatz ist zu schwach, wenn er nur weitere Fliesstext-Erklaerung erzeugt, aber keinen klaren, wiederverwendbaren Export- oder Repro-Pfad schafft.

## Arbeitsvertrag

- Fuehre keinen breiten Re-Scan der Harness-Engine durch.
- Oeffne keine zweite Verbesserungsscheibe, bevor die erste valide umgesetzt und geprueft ist.
- Behandle widerspruechliche Artefakte als Harness-Finding, nicht als Anlass fuer implizite Annahmen.
- Erzwinge neue Regeln nach Moeglichkeit als Test, Contract-Check, Script oder maschinenlesbare Ausgabe.
- Verwirf einen Ansatz sofort, wenn der erste schmale Check ihn widerlegt.
- Erfinde keine fehlenden Artefaktinhalte; Unsicherheit bleibt Unsicherheit.
- Nutze bestehende Artefakte nur zur Defektwahl, Priorisierung und Validierungsvorbereitung.
- Markiere wichtige Aussagen als `repo`, `extern-oeffentlich`, `extern-vertraulich` oder `hypothese`.

## Nicht Tun

- kein neues Voll-Audit
- kein paralleles Bearbeiten von FU-003 und FU-004 in einem Lauf
- keine allgemeine Backlog-Prosa statt Defektauswahl
- keine stillschweigende Annahme, dass der neueste Artefaktordner automatisch vollstaendig oder widerspruchsfrei ist
- keine Abschlussmeldung ohne enge Validierung
- keine neuen `work_artifacts/harness_followup_<YYYY-MM-DD>/`-Ordner
- keine neue Hilfsabstraktion, wenn ein lokaler Eingriff denselben Vertrag guenstiger herstellen kann
- keine Doku-Reparatur als Ersatz fuer einen fehlenden Check

## Ausgabeform

Halte Auswahl, Hypothese, Validierung und Rest-Risiko im Chat knapp fest. Persistente Aenderungen gehoeren primaer in Code, Tests, Contract-Checks, Scripts oder eine zwingend mitbetroffene bestehende Doku.

## Workflow

1. **Artefakte lesen und Defekt waehlen.** Lies nur die noetigen Artefakte, waehle den naechsten offenen Defekt und gib die vier Pflichtpunkte aus.
2. **Direkt kontrollierende Stelle finden.** Springe vom Artefakt zum kleinsten Ort, der den Defekt wirklich erzeugt, erzwingt oder validiert. Wenn ein Einstiegspfad nur weiterleitet, gehe einen Hop tiefer.
3. **Kleinsten wirksamen Eingriff festlegen.** Benenne Zieloberflaeche, minimale Dateiflaeche, erwartetes neues Invariant und ersten Validierungsschritt.
4. **Eng implementieren.** Implementiere nur die eine Verbesserung, die den gewaehlten Defekt direkt reduziert.
5. **Sofort validieren.** Fuehre nach der ersten substanziellen Aenderung sofort den schmalsten passenden Check aus. Lies das Ergebnis vollstaendig. Bei Scheitern: lokale Reparatur oder Defektwahl verwerfen.
6. **Rest-Risiko neu einordnen.** Halte fest, ob der Defekt geschlossen, reduziert oder widerlegt ist und welcher offene Hebel jetzt uebrig bleibt.

Wenn die Validierung die Defektwahl widerlegt, springe genau einen Hop zur naechsten direkt kontrollierenden Stelle. Oeffne keinen neuen breiten Suchlauf.

## Typische Checks

```bash
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
make agent-harness-check
```

Nutze den schmalsten passenden Check zuerst. Nur wenn kein ausfuehrbarer Check existiert, auf Diff-Inspektion zurueckfallen.

## Abschlussbericht

Nutze fuer den Abschlussbericht nur dieses Raster:

```text
- Defekt: ...
- Evidenz: ...
- Implementierter Eingriff: ...
- Validierung: ...
- Status: geschlossen | reduziert | widerlegt
- Naechster Hebel: ...
```

## Done-Definition

Erfolg bedeutet: Ein offener Defekt aus den Harness-Artefakten wurde in eine direkte Repo-Aenderung uebersetzt, eng validiert und ohne neuen Artefaktlauf geschlossen oder messbar reduziert.

Wenn sich der ausgewaehlte Defekt nicht schmal und sicher umsetzen laesst, stoppe nicht mit allgemeiner Prosa. Benenne praezise, welche fehlende Evidenz, welche blockierende Grenze oder welcher billigere Vorlaeufer-Schritt zuerst noetig ist.