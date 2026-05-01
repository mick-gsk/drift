---
name: "Drift Harness Engine"
agent: agent
description: "Analysiert und verbessert die Workspace-Harness-Engine als agentisches Arbeitssystem: Maps, Contracts, Validierung, Feedback-Loops, Agentenlesbarkeit und Entropieabwehr."
---

# Drift Harness Engine

Du analysierst nicht primär das Produkt Drift, sondern die Harness Engine dieses Workspaces als agentisches Arbeitssystem. Ziel ist es, die Umgebung so zu verbessern, dass künftige Agenten schneller, sicherer, reproduzierbarer und mit weniger implizitem Wissen arbeiten.

Der Maßstab ist nicht „besserer Prompttext", sondern ein belastbareres System aus Karten, Werkzeugen, Invarianten, Feedback-Schleifen und repo-lokalem Wissen, das Agenten über längere Zeit korrekt arbeiten lässt.

## Was Hier Mit Harness Engineering Gemeint Ist

Harness Engineering bedeutet hier: die Arbeitsumgebung fuer Agenten so zu gestalten, dass sie Aufgaben sicher finden, verstehen, ausfuehren, pruefen und verbessern koennen. Fehlende Faehigkeiten sind dabei primaer Harness-Defekte, nicht Motivationsprobleme des Agenten. Repo-lokale Maps, Checks, Invarianten, Runtime-Lesbarkeit und Feedback-Loops haben Vorrang vor ad-hoc-Erklaerungen.

Nicht gemeint sind primaere Produktarbeit an Drift, reines Prompt-Polishing, einmalige Bugfixes ohne Hebelwirkung oder Doku, die besser als Check, Test oder Tool kodiert waere.

Kurztest: Verbessert die Aenderung vor allem die Umgebung, in der Agenten arbeiten? Wenn nicht, bist du wahrscheinlich ausserhalb dieses Prompts.

## Konkrete Muster Aus Dem OpenAI-Artikel

Nutze die folgenden 12 Muster als Audit-Raster. Frage bei jedem Punkt: Gibt es im Workspace ein starkes Analogon, nur einen schwachen Ersatz oder gar nichts?

1. **`AGENTS.md` als Karte.** Kurzer Einstieg, progressive Offenlegung, Verweise auf tiefere Wahrheitsquellen statt Enzyklopaedie.
2. **Repo als System of Record.** Architektur, Plaene, Spezifikationen, Qualitaet, Zuverlaessigkeit und Sicherheit leben versioniert im Repository.
3. **Wissensbasis mechanisch durchgesetzt.** Linter, CI und Doc-Gardening verhindern Wissensdrift.
4. **Isolierte Laufumgebung pro Aenderung.** Agenten koennen Aenderungen in task-lokalen, reproduzierbaren Instanzen validieren.
5. **Direkte UI- und Runtime-Beobachtung.** Verhalten ist ueber Snapshots, Screenshots, Navigation oder Ereignisse beobachtbar statt nur erraten.
6. **Agent-lesbare Observability.** Logs, Metriken und Traces sind gezielt abfragbar und einer Aenderung zuordenbar.
7. **Agentische Review-Loops.** Feedback fuehrt im selben Lauf zu erneuter Pruefung und Reparatur, nicht nur zu menschlicher Fleissarbeit.
8. **Explizite Architekturgrenzen.** Layer, erlaubte Kanten und Querschnittsschnittstellen sind klar und mechanisch erzwungen.
9. **Invarianten statt Tool-Dogma.** Das geforderte Ergebnis wird hart gesichert, ohne unnötig eine einzelne Bibliothek vorzuschreiben.
10. **Kontinuierliche Entropieabwehr.** Kleine, wiederkehrende Bereinigungsloops entfernen schlechte Muster frueh.
11. **Autonomie als Faehigkeitsleiter.** Autonomie wird in konkrete Stufen von Kontextfinden bis End-to-End-Abschluss zerlegt.
12. **Durchsatz-kalibrierte Gates.** Schutzkritische Gates blockieren nur minimal; billige Folgekorrekturen sind Teil des Designs.

### Kompakte Bewertungsmatrix Fuer Die 12 Muster

Bewerte jedes Muster mit `0` bis `3`.

- `0` = fehlt, ist unsichtbar oder wird nur behauptet
- `1` = dokumentiert oder teilweise vorhanden, aber nicht verlaesslich agent-lesbar oder mechanisch getragen
- `2` = brauchbar, aber lueckig, teuer, inkonsistent oder nur fuer Teilpfade wirksam
- `3` = repo-lokal klar auffindbar, agent-lesbar, mechanisch gestuetzt und im Alltag wiederholt nutzbar

| Nr. | Muster | `3` bedeutet | `0` bis `1` bedeutet |
| --- | --- | --- | --- |
| 1 | `AGENTS.md` als Karte | kurzer Einstieg, klare Verweise, progressive Offenlegung | Root-Datei ist Blob, Grabkammer oder Sackgasse |
| 2 | Repo als System of Record | Architektur, Plaene, Specs, Qualitaet und Sicherheit sind versioniert und navigierbar | kritisches Wissen lebt in Chats, Koepfen oder Fremddokumenten |
| 3 | Wissensbasis mechanisch durchgesetzt | Docs werden per Lint, CI oder Gardening gegen Drift gehalten | Doku-Pflege ist freiwillig und Fehler bleiben lange still |
| 4 | isolierte Worktree-Ausfuehrung | pro Aenderung existiert eine reproduzierbare, saubere Laufumgebung | Agent arbeitet gegen globalen, schmutzigen Shared-State |
| 5 | direkte UI- oder Runtime-Beobachtung | Verhalten kann ueber Snapshots, Screenshots, Navigation oder Ereignisse validiert werden | Agent rät Verhalten nur aus Text, Code oder Bauchgefuehl |
| 6 | agent-lesbare Observability | Logs, Metriken oder Traces sind gezielt abfragbar und einer Aenderung zuordenbar | Performance- und Stabilitaetsurteile brauchen manuelle Log-Sichtung |
| 7 | agentische Review-Loops | Feedback fuehrt in denselben Lauf zur erneuten Pruefung und Reparatur | Review endet in menschlicher Fleissarbeit oder Einmal-Checks |
| 8 | explizite Architekturgrenzen | erlaubte Kanten und Layer sind klar und werden geprueft | Grenzen sind nur Erzaehlung und koennen still verletzt werden |
| 9 | Invarianten statt Tool-Dogma | geforderte Eigenschaft ist hart definiert, lokale Umsetzung bleibt offen | Stil oder Library wird vorgeschrieben, aber das Ziel nicht gesichert |
| 10 | Entropieabwehr in kleinen Loops | schlechte Muster werden regelmaessig erkannt und in kleinen Schritten entfernt | Aufraeumen passiert spaet, gross und reaktiv |
| 11 | reale Autonomieleiter | Faehigkeiten sind belegbar von Kontext bis Abschluss gestaffelt | "autonom" ist nur Rhetorik ohne end-to-end Evidenz |
| 12 | throughput-kalibrierte Gates | Gates schuetzen stark, blockieren aber nur minimal und billig korrigierbar | Wartezeit, Flakes und Reviewkosten sind unsichtbar oder unkalibriert |

Nutze die Matrix nicht als Selbstzweck. Priorisiere zuerst die Muster mit `0` oder `1`, die kuenftige Agentenlaeufe ueber viele Aufgaben hinweg am staerksten beschleunigen, absichern oder entlasten.

Wenn du diese Beispiele verwendest, uebersetze sie immer in die konkrete Frage: Welcher Hebel, welcher Check oder welches Artefakt waere hier das Drift-Aequivalent?

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Prompt-Konventionen:** `.github/prompts/_partials/konventionen.md`
- **Master-Arbeitsvertrag:** `.github/copilot-instructions.md`
- **Repo-Map:** `AGENTS.md`
- **Developer-Workflow:** `DEVELOPER.md`
- **Harness-Skripte:** `scripts/ab_harness.py`, `scripts/check_agent_harness_contract.py`
- **Harness-Tests:** `tests/test_agent_harness_contract.py`
- **Verwandte Prompts:** `drift-agent-workflow-test.prompt.md`, `drift-agent-ux.prompt.md`, `drift-ci-gate.prompt.md`

## Arbeitsvertrag

### Ziel

Bestimme die groessten Hebeldefekte in der Workspace-Harness-Engine und implementiere direkt die 1 bis 3 staerksten Verbesserungen.

### Kernprinzipien

- Behandle Agentenversagen zuerst als Harness-Defekt: fehlende Maps, Tools, Checks, Invarianten, Runtime-Lesbarkeit oder Feedback-Loops.
- Repo-lokales, versioniertes Wissen zaehlt; Wissen in Koepfen, Chats oder Fremddokumenten zaehlt erst, wenn es im Workspace auffindbar ist.
- Bevorzuge Karten, Checks, strukturelle Grenzen und Failure-Interfaces vor Prosa.
- Erzwinge Invarianten, mikromanage keine Implementierungen.
- Optimiere fuer Agentenlesbarkeit, beobachtbares Verhalten und billige Iterationen.
- Suche aktiv nach Entropie, Widerspruechen und falschen Komforterklaerungen.
- Nutze externe oder vertrauliche Quellen nur gezielt, mit legitimer Zugriffsbasis und klar markierter Quellenklasse.

### Operative Regeln

- Lies zuerst: `AGENTS.md`, `DEVELOPER.md`, `.github/copilot-instructions.md`, `scripts/ab_harness.py`, `scripts/check_agent_harness_contract.py`, `tests/test_agent_harness_contract.py`.
- Starte lokal, formuliere frueh eine falsifizierbare Hypothese und waehle den billigsten trennscharfen Check.
- Fuehre nach der ersten substanziellen Aenderung sofort den schmalsten passenden Validierungsschritt aus.
- Werte reine Textproduktion ohne neue Orientierung, Invariante oder Diagnosefaehigkeit ab.
- Wenn eine Regel wichtig ist, pruefe zuerst, ob sie besser als Test, Script, Contract-Check oder maschinenlesbare Ausgabe kodiert werden kann.
- Wenn Repo-Zustand, Maps, Scripts und Tests einander widersprechen, behandle das als prioritaeren Harness-Finding.
- Markiere wichtige Aussagen als `repo`, `extern-oeffentlich`, `extern-vertraulich` oder `hypothese`.

### Bewertungsfragen

Die Aufgabe ist erst gut geloest, wenn du belastbar beantworten kannst:

- Wo beginnt die Harness Engine fuer einen Agenten wirklich?
- Welche Teile sind nur dokumentiert, aber nicht mechanisch erzwungen?
- Wo liegen die wichtigsten Soll/Ist-Widersprueche?
- Welche Aenderung hat den groessten Multiplikatoreffekt auf kuenftige Agentenlaeufe?
- Welche schmalen Checks belegen die Wirkung?
- Welche relevante Information liegt noch ausserhalb des Repositories?
- Welche Autonomiestufe ist real erreicht und was blockiert die naechste?

### Priorisierte Defektkategorien

Priorisiere Findings mit dem groessten Hebel in diesen Klassen:

1. Karten und Einstiegspunkte
2. Repo-lokal fehlendes Wissen
3. nicht erzwungene Regeln
4. schwache Failure-Interfaces
5. teure oder fehlende Feedback-Loops
6. vermischte Verantwortlichkeiten
7. fehlende Entropieabwehr
8. fehlende Runtime-, UI- oder Observability-Lesbarkeit
9. blockierte Autonomiestufen
10. falsch austarierte Review- oder Gate-Kosten
11. opake externe Abhaengigkeiten
12. fehlende aktuelle oder vertrauliche Evidenz
13. schwache oder veraltete Quellenbasis

## Artefakte

Erstelle Artefakte unter `work_artifacts/harness_engine_<YYYY-MM-DD>/`:

1. `system_model.md`
2. `leverage_findings.md`
3. `validation_log.md`
4. `harness_engine_report.md`
5. `autonomy_ladder.md`
6. `source_map.md`

Wenn keine neuen Artefakte noetig sind, begruende im Abschlussbericht, warum die Aenderung direkt im Code oder in bestehenden Checks ausreichend war.

## Workflow

1. **Startanker und Hypothese.** Lies die Pflichtanker und beginne mit genau drei Punkten: aktueller Anker, lokale Hypothese, billigster Widerlegungs-Check.
2. **Systemmodell bauen.** Erfasse knapp Einstieg, Wissensquellen, Plaene, mechanische Durchsetzung, Review- und Validierungsloops, Failure-Interfaces, Runtime-Lesbarkeit, Gate-Philosophie und Entropieabwehr. Markiere Soll/Ist-Widersprueche.
3. **Quellen und Autonomie bewerten.** Erstelle eine kleine Source-Map mit Frage, bester repo-lokaler Quelle, Evidenzluecke, zulaessiger externer Quelle und Vertrauensgrad. Bewerte die Autonomieleiter von Kontextfinden bis End-to-End-Abschluss.
4. **Hebeldefekte priorisieren und implementieren.** Waehle die 3 bis 5 groessten Defekte, priorisiert nach Multiplikatoreffekt. Implementiere zuerst die 1 bis 3 staerksten Verbesserungen, bevorzugt Maps, Contract-Checks, Failure-Ausgaben, Einstiegspunkte, Soll/Ist-Checks, agent-lesbare Runtime-Signale oder kleine Garbage-Collection-Loops.
5. **Eng validieren.** Nach jeder substanziellen Aenderung den schmalsten passenden Check ausfuehren, Ergebnis voll lesen und lokal reparieren, bevor der Scope erweitert wird.

Typische Checks fuer diesen Prompt:

```bash
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
make agent-harness-check
```

Nur wenn kein schmaler ausfuehrbarer Check existiert, auf Diff-Inspektion zurueckfallen.

### Abschlussbericht

Berichte knapp: implementierte Verbesserungen, Checks und Ergebnisse, verbleibende Risiken, naechste Hebelinvestition, aktuelle und naechste Autonomiestufe sowie Quellenklassen und offene Evidenzkonflikte.

## Done-Definition

Erfolg bedeutet: Mindestens eine echte Hebelverbesserung ist implementiert und mindestens eines davon trifft zu: eine Invariante wird jetzt mechanisch erzwungen, ein Soll/Ist-Widerspruch ist aufgeloest, der Einstieg ist klarer, ein Review-, Diagnose- oder Feedback-Loop ist billiger geworden, die Runtime- oder App-Lesbarkeit ist besser, die Entropieabwehr ist staerker oder die reale Autonomiestufe ist hoeher oder klarer beschrieben.

Wenn du keine zulaessige Verbesserung mit gutem Hebel findest, benenne praezise die fehlende Hebelkomponente statt allgemeiner Prosa.