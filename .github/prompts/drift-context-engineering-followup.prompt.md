---
name: "drift-context-engineering-followup"
agent: agent
description: "Uebersetzt einen offenen Kontext-Luecken-Befund aus einem Context-Engineering-Audit direkt in eine schmale Repo-Aenderung: liest bestehende Artefakte, waehlt den naechsten offenen Hebel und setzt genau eine eng validierte Kontext-Verbesserung um."
---

# Drift Context Engineering Follow-up

Nutze diesen Prompt nach einem Lauf von `drift-context-engineering`, wenn unter `work_artifacts/context_engineering_<YYYY-MM-DD>/` bereits ein Artefaktordner existiert und genau die naechste offene Kontextluecke umgesetzt werden soll.

Du fuehrst **kein** neues Context-Engineering-Audit durch. Du liest nur so viel aus den vorhandenen Artefakten, wie noetig ist, um den naechsten offenen Kontext-Hebel zu waehlen, und setzt dann genau **eine** schmale Verbesserung direkt im Repository um.

Der Prompt ist nur erfolgreich, wenn aus dem Artefakt-Gap eine reale Code-, Script-, Contract-, Test- oder Doku-Aenderung wird, die einen Agenten spaeter schneller oder sicherer mit dem richtigen Kontext versorgt. Neue Folge-Artefakte, neue Gap-Listen oder ein zweites Audit zaehlen hier nicht als Fortschritt.

## Was Hier Mit Follow-up Gemeint Ist

Follow-up bedeutet in diesem Prompt:

- einen bereits identifizierten Kontext-Gap aus vorhandenen Artefakten in eine direkte Repo-Aenderung uebersetzen
- die Auswahl auf den naechsten offenen Hebel fokussieren statt die Context-Engineering-Landschaft erneut zu vermessen
- den Gap so schmal bearbeiten, dass ein enger Check die Wirkung oder Widerlegung schnell zeigen kann

Nicht gemeint sind:

- ein neues Context-Engineering-Voll-Audit
- ein weiterer Artefaktlauf unter `work_artifacts/`
- allgemeine Zusammenfassungen oder Freshness-Strategietexte ohne direkte Umsetzung
- paralleles Abarbeiten mehrerer plausibler Luecken in einem Lauf

Kurztest: Wenn der naechste Schritt nicht in einer direkten Aenderung an Code, Tests, Scripts, Contract-Checks, Maps oder einer zwingend betroffenen Kontrollflaeche endet, bist du noch nicht im Follow-up.

> **Pflicht:** Vor Ausfuehrung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- `.github/instructions/drift-policy.instructions.md`
- `.github/prompts/_partials/konventionen.md`
- `.github/prompts/_partials/context-engineering-contract.md`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- `DEVELOPER.md`
- `scripts/check_agent_harness_contract.py`
- `tests/test_agent_harness_contract.py`
- `drift-context-engineering.prompt.md`
- `drift-harness-followup.prompt.md`

## Eingabe

Erwarte einen vorhandenen Artefaktordner unter `work_artifacts/context_engineering_<YYYY-MM-DD>/`.

Lies daraus mindestens:

- `context_engineering_report.md`
- `context_gaps.md`

Ziehe `context_map.md` und `freshness_status.md` nur dann hinzu, wenn der naechste Gap ohne sie nicht sauber eingegrenzt werden kann.

Wenn kein Context-Engineering-Artefaktordner existiert: stoppe und verweise zuerst auf `drift-context-engineering`.

Wenn mehrere Artefaktordner existieren: verwende standardmaessig den neuesten, ausser der User nennt einen anderen.

Wenn einer der beiden Pflichtartefakte fehlt, stoppe nicht stillschweigend. Benenne exakt, welche Datei fehlt, welcher Teil der Gap-Wahl dadurch unsicher wird und ob trotzdem ein enger Follow-up-Lauf mit reduzierter Sicherheit moeglich ist.

Wenn der Gap auf ein Problem ausserhalb des Repositories zeigt, das repolokal nicht durch eine Aenderung schliessbar ist, benenne die Grenze und verweise auf den naechsten zulaessigen Hebel, der innerhalb des Repositories liegt.

## Pflichtausgabe Vor Dem Ersten Edit

Bevor du irgendetwas implementierst, gib genau diese vier Punkte aus:

1. verwendeter Artefaktordner
2. ausgewaehlter Gap mit Gap-ID oder Kurzname aus `context_gaps.md`
3. lokale Hypothese, warum genau dieser Gap der naechste Hebel ist
4. billigster Check, der diese Hypothese falsifizieren kann

Wenn du diese vier Punkte nicht sauber benennen kannst, darfst du noch nicht editieren.

## Ziel

Setze genau **eine** fokussierte Folgeverbesserung um, basierend auf dem hoechsten noch offenen Kontext-Hebel aus den Artefakten.

Standard-Priorisierung:

1. offener Gap mit expliziter Priorisierung in `context_gaps.md` oder im Report
2. Gap, der die Autonomieleiter am staerksten blockiert
3. Gap, der mit dem schmalsten Check am billigsten falsifizierbar ist

Tie-Breaker in dieser Reihenfolge:

1. Gap, der einen impliziten statischen Kontext in einen repo-lokalen, versionierten Einstiegspunkt ueberfuehrt
2. Gap, der einen losen dynamischen Kontext (Working-Tree-Status, letzter Check) maschinenlesbar macht
3. Gap, der eine Single-Source-of-Truth-Luecke durch einen mechanischen Vertrag schliesst
4. Gap, der mit bestehenden Dateien und Tests umgesetzt werden kann

Oeffne keinen neuen Gap, solange ein hoeher priorisierter offener Gap aus den Artefakten noch nicht bewusst verworfen wurde.

Wenn du vom priorisierten Gap abweichst, musst du explizit benennen:

- welcher hoehere Gap verworfen wurde
- wodurch er im aktuellen Lauf blockiert ist
- warum der neue Gap trotzdem der hoehere unmittelbare Hebel ist

## Konkreter Implementierungsvertrag

- Setze genau **eine** Verbesserungsscheibe um.
- Beruehre nur die Dateien, die den gewaehlten Gap direkt kontrollieren, plus die kleinste noetige Test- oder Doku-Flaeche.
- Wenn der Gap mit einem Test, Contract-Check oder maschinenlesbaren Export schliessbar ist, bevorzuge das gegenueber reiner Prosa.
- Wenn der erste Eingriff nur Doku aendert, obwohl ein Check oder Script moeglich waere, ist der Ansatz zu schwach und muss geschaerft werden.
- Fuehre keine zweite benachbarte Verbesserung ein, nur weil sie bequem erscheint.
- Erzeuge keine neuen Folge-Artefakte unter `work_artifacts/`, solange der User das nicht ausdruecklich verlangt.
- Wenn mehrere kleine Dateien plausibel sind, bevorzuge die direkt kontrollierende Stelle vor einer neuen Hilfsabstraktion.
- Wenn ein bestehender Contract-Check fast den gesuchten Vertrag ausdrueckt, schaerfe ihn statt einen parallelen Mechanismus einzufuehren.

**Statischer-Kontext-Gap:** stark ist eine Massnahme, wenn sie eine Information aus Chats, Koepfen oder Fremddokumenten in eine versionierte, repo-lokale Datei ueberfuehrt und damit fuer spaetere Agenten ohne Terminal-Archaeologie findbar macht.

**Dynamischer-Kontext-Gap:** stark ist eine Massnahme, wenn sie einen losen Laufzeit-Status in eine maschinenlesbare, datierte und agent-lesbare Form bringt, z.B. als Repro-Bundle, Check-Ausgabe oder Session-Artefakt.

**Freshness-Gap:** stark ist eine Massnahme, wenn sie einen Mechanismus schafft, der Agenten explizit signalisiert, wie alt eine Kontextquelle ist, statt Aktualitaet stillschweigend vorauszusetzen.

Zu schwach ist ein Ansatz, wenn er nur weitere Fliesstext-Erklaerung erzeugt, aber keinen klar wiederverwendbaren oder maschinenlesbaren Kontext-Pfad schafft.

## Arbeitsvertrag

- Fuehre keinen breiten Re-Scan durch.
- Oeffne keine zweite Verbesserungsscheibe, bevor die erste valide umgesetzt und geprueft ist.
- Behandle widerspruechliche Artefakte als Context-Engineering-Finding, nicht als Anlass fuer implizite Annahmen.
- Erzwinge neue Regeln nach Moeglichkeit als Test, Contract-Check, Script oder maschinenlesbare Ausgabe.
- Verwirf einen Ansatz sofort, wenn der erste schmale Check ihn widerlegt.
- Erfinde keine fehlenden Artefaktinhalte; Unsicherheit bleibt Unsicherheit.
- Markiere wichtige Aussagen als `repo`, `extern-oeffentlich`, `extern-vertraulich` oder `hypothese`.

## Nicht Tun

- kein neues Context-Engineering-Voll-Audit
- kein paralleles Abarbeiten mehrerer Gaps in einem Lauf
- keine allgemeine Freshness-Prosa statt Gap-Wahl
- keine stillschweigende Annahme, dass der neueste Artefaktordner automatisch vollstaendig oder widerspruchsfrei ist
- keine Abschlussmeldung ohne enge Validierung
- keine neuen `work_artifacts/context_engineering_followup_<YYYY-MM-DD>/`-Ordner
- keine neue Hilfsabstraktion, wenn ein lokaler Eingriff denselben Vertrag guenstiger herstellen kann
- keine Doku-Reparatur als Ersatz fuer einen fehlenden Check

## Ausgabeform

Halte Gap-Wahl, Hypothese, Validierung und Rest-Risiko im Chat knapp fest. Persistente Aenderungen gehoeren primaer in Code, Tests, Contract-Checks, Scripts, Maps oder eine zwingend mitbetroffene bestehende Doku.

## Workflow

1. **Artefakte lesen und Gap waehlen.** Lies nur die noetigen Artefakte, waehle den naechsten offenen Gap und gib die vier Pflichtpunkte aus.
2. **Direkt kontrollierende Stelle finden.** Springe vom Artefakt zum kleinsten Ort, der den Gap wirklich erzeugt, erzwingt oder validiert. Wenn ein Einstiegspfad nur weiterleitet, gehe einen Hop tiefer.
3. **Kleinsten wirksamen Eingriff festlegen.** Benenne Zieloberflaeche, minimale Dateiflaeche, erwartetes neues Invariant und ersten Validierungsschritt.
4. **Eng implementieren.** Implementiere nur die eine Verbesserung, die den gewaehlten Gap direkt reduziert.
5. **Sofort validieren.** Fuehre nach der ersten substanziellen Aenderung sofort den schmalsten passenden Check aus. Lies das Ergebnis vollstaendig. Bei Scheitern: lokale Reparatur oder Gap-Wahl verwerfen.
6. **Rest-Risiko neu einordnen.** Halte fest, ob der Gap geschlossen, reduziert oder widerlegt ist und welcher offene Hebel jetzt uebrig bleibt.

Wenn die Validierung die Gap-Wahl widerlegt, springe genau einen Hop zur naechsten direkt kontrollierenden Stelle. Oeffne keinen neuen breiten Suchlauf.

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
- Gap: ...
- Evidenz: ...
- Implementierter Eingriff: ...
- Validierung: ...
- Status: geschlossen | reduziert | widerlegt
- Naechster Hebel: ...
```

## Done-Definition

Erfolg bedeutet: Ein offener Kontext-Gap aus den Context-Engineering-Artefakten wurde in eine direkte Repo-Aenderung uebersetzt, eng validiert und ohne neuen Artefaktlauf geschlossen oder messbar reduziert.

Wenn sich der ausgewaehlte Gap nicht schmal und sicher umsetzen laesst, stoppe nicht mit allgemeiner Prosa. Benenne praezise, welche fehlende Evidenz, welche blockierende Grenze oder welcher billigere Vorlaeufer-Schritt zuerst noetig ist.
