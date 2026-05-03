# Research: CLI Load Reduction

## Decision 1: Help-Struktur nach Capability-Areas statt flacher Top-Level-Liste
- Decision: Die Help-Ausgabe wird in Aufgabenbereiche gegliedert (z. B. Einstieg, Analyse, Qualitaet, Reports, Wartung).
- Rationale: Nutzer suchen nach Intention, nicht nach internem Command-Namen; strukturierte Gruppen reduzieren Suchaufwand und kognitive Last.
- Alternatives considered: Rein alphabetische Liste mit kuerzeren Beschreibungen; verworfen, weil weiterhin keine Zielnavigation entsteht.

## Decision 2: Gefuehrter Entry-Path als erste Sektion in `drift --help`
- Decision: Oberste Help-Sektion zeigt einen klaren "Start hier"-Pfad mit wenigen empfohlenen Erstschritten.
- Rationale: Erstnutzer brauchen in den ersten Sekunden handlungsfaehige Orientierung; ein fokussierter Einstieg verbessert Aktivierungsrate.
- Alternatives considered: Nur Verweis auf externe Doku; verworfen, weil der CLI-Einstieg ohne Kontextwechsel funktionieren muss.

## Decision 3: Additive Migration ohne Breaking Changes
- Decision: Bestehende Command-Aufrufe bleiben unveraendert; nur Darstellung und Navigationspfade werden neu strukturiert.
- Rationale: Akzeptanz steigt, wenn etablierte Skripte stabil bleiben und dennoch bessere Orientierung verfuegbar ist.
- Alternatives considered: Renaming/Entfernen alter Top-Level-Kommandos; verworfen wegen hohem Migrationsrisiko.

## Decision 4: Contract-Tests fuer Help-Navigation und Legacy-Kompatibilitaet
- Decision: Neben Unit-Tests werden CLI-Contract-Tests fuer sichtbare Help-Struktur und Legacy-Aufrufstabilitaet definiert.
- Rationale: Das Feature ist UX-getrieben; daher muss die oeffentliche CLI-Oberflaeche als Vertrag abgesichert sein.
- Alternatives considered: Nur Snapshot-Tests einzelner Help-Strings; verworfen, da zu fragil und semantisch zu schwach.

## Decision 5: Keine neue Persistenz oder Telemetrie als Teil von v1
- Decision: Scope bleibt auf statischer, zur Laufzeit berechneter Help-Navigation ohne neue Datenspeicher.
- Rationale: Erfuellt YAGNI, minimiert Komplexitaet und liefert schnellen, risikoarmen Nutzen.
- Alternatives considered: Nutzungsbasierte adaptive Reihenfolge; vertagt auf spaeteres Inkrement mit gesonderter Evidenz.