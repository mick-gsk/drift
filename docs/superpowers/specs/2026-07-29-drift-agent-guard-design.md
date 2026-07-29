# Drift Agent Guard — Design

**Datum:** 2026-07-29 · **Status:** Entwurf zur Umsetzung · **Autor:** Claude Code Session (Analyse + Design)

---

## 1. Kernthese

> **Dein Agent baut es zum zweiten Mal — drift sagt es ihm, bevor er es tut.**

Drift wird ein Claude-Code-Plugin, das im Agent-Loop wirkt: vor jeder Datei-Änderung sagt es dem
Agenten, was hier schon existiert und welche Grenze gilt; nach der Änderung sagt es, ob er gerade
etwas dupliziert oder eine Grenze verletzt hat. Der Nutzer sieht am Ende jeder Session eine Zahl:
*so oft hat drift heute eine Duplizierung verhindert.*

Alles, was dieser These nicht dient, ist in diesem Vorhaben nicht enthalten.

---

## 2. Warum context-mode erfolgreich ist (Evidenz)

Gemessen am 2026-07-29 über GitHub-API, npm-Registry-API und lokale Plugin-Installation:

| | context-mode | drift |
|---|---|---|
| Erstes Commit | 2026-02-23 | 2026-03-18 |
| GitHub Stars | 19.438 | 13 |
| Forks | 1.381 | 10 |
| Installs | 88.034 npm/Monat | 1.629 PyPI/Monat |
| Quellcode | 41.617 LOC / 95 Dateien | 92.665 LOC / 344 Dateien |
| Nutzer-Oberfläche | 11 MCP-Tools, 7 Slash-Commands | 47 CLI-Commands, 30 Signale, 60 CI-Workflows, 477 .md |
| Laufzeit-Deps | 8 | 6 (+8 Extras-Gruppen) |
| Launch | HN #1, 570 Punkte, 100 Kommentare | — |

### Der wichtigste Befund

**context-mode ist innen nicht minimalistisch.** 41.617 LOC, 95 Quelldateien, eine Testsuite mit
6.718 Zeilen allein für `server.test.ts`, Adapter für 17 Plattformen. Minimalistisch ist
ausschließlich die *Oberfläche* — und zwar deshalb, weil jede dieser 41.617 Zeilen **einem einzigen
Versprechen** dient.

Drifts 92.665 LOC dienen ~15 Versprechen. Das eigene Audit beziffert es: das Kernversprechen wird
von **6 der 46 CLI-Commands** geliefert; der gepflegte Surface ist ~3× so groß wie das
Kernversprechen erfordert (Kern ~32,8 % / Agent-MCP-Surface ~32,7 % / CLI+Glue ~34,5 %).

**Der Unterschied ist also nicht Codegröße. Er ist Versprechen-pro-Codezeile.**

### Die sechs übertragbaren Prinzipien

1. **Ein Problem, das der Nutzer schon spürt.** „Nach 30 Minuten sind 40 % deines Kontexts weg" —
   das erlebt jeder Claude-Code-Nutzer täglich. „Cross-file structural coherence erosion" erlebt
   niemand; man muss erst überzeugt werden, dass es das Problem gibt.
2. **Ein Mechanismus, der in einem Satz und einem Code-Snippet erklärbar ist.** context-modes README
   erklärt das Prinzip mit 4 Zeilen JavaScript („statt 47 × Read = 700 KB → 1 × ctx_execute = 3,6 KB").
3. **Wert wird gefühlt, nicht bewiesen.** Bemerkenswert: Auf HN wird genau das kritisiert — *„the
   claimed 98% context savings are noise without benchmarks of harness performance"* (clouedoc),
   *„have you tested it on any benchmark or eval?"* (nharada). Der Autor hat keine belastbare
   Wirksamkeitsstudie. **Trotzdem 19.438 Stars** — weil der Nutzer die Wirkung in *seiner* Session
   sieht (Statusleiste, gesparte Dollar, längere Sessions). Für drift heißt das: die fehlende
   Outcome-Validierung ist nicht das Adoptionshindernis. Das Hindernis ist, dass man **nichts spürt**.
4. **Null Entscheidungen bei der Installation.** Zwei Zeilen, Neustart, fertig — Routing kommt
   automatisch über SessionStart-Hook, es wird keine Datei ins Projekt geschrieben. drift verlangt
   heute: Profil wählen, `drift.yaml`, Baseline, Suppressions.
5. **Distribution ist Produktbestandteil, nicht Marketing.** Ein `ctx_doctor`, der die eigene
   Installation verifiziert. 17 Plattformen, je ein Ein-Zeilen-Install. Drift hat **keinen einzigen
   Claude-Code-Plugin-Manifest** — obwohl ein MCP-Server (2.074 LOC) existiert.
6. **Der Beweis läuft mit.** `ctx_stats` und die Statusleiste zeigen den Nutzen dauerhaft. Der Nutzer
   erlebt den Gewinn immer wieder — und erzählt davon.

---

## 3. Warum drift heute nichts bringt (Messung, nicht Meinung)

Gemessen am 2026-07-29 im drift-Repo selbst (344 Python-Dateien, warme `.drift-cache` mit 7.780
Parse-Einträgen), Python 3.12.13, drift 2.51.1, macOS/arm64:

| Aufruf | Zeit | Ergebnis |
|---|---|---|
| `python -c "import drift.cli"` (Dev-Env mit `[embeddings]`) | **3,33 s** | — |
| `drift --help` (Dev-Env) | **3,35 s** | — |
| `python -c "import drift.cli"` (Clean-Install simuliert) | **0,38 s** | — |
| `drift --help` (Clean-Install simuliert) | **0,35 s** | — |
| `drift context --for-agent -t <datei>` | **0,42 s kalt / 0,37 s warm** | 1.938 B JSON |
| `drift verify --scope <eine datei> --format json` | **461,65 s kalt / 213,78 s warm** | 6.049 B JSON |

**Befund A — Import-Steuer.** 3,0 der 3,35 s entstehen, weil `drift.cli` über die Kette
`commands.brief → api → api.shadow_verify → analyzer → pipeline → embeddings` eager
`sentence_transformers → transformers → sklearn` lädt. Diese Steuer zahlt **jeder** Aufruf,
auch `drift --help`. Wer `pip install 'drift-analyzer[all]'` folgt, bekommt genau diese 3,35 s.

**Befund B — Der schnelle Pfad ist leer.** `drift context --for-agent` lieferte für alle vier
geprüften Dateien (`pipeline.py`, `mcp_server.py`, `pattern_fragmentation.py`, `cli.py`)
identisch `invariants: 0`, `active_signals_affecting: 0`, `known_findings: 0` — ein Gerüst aus
`agent_instruction` / `next_tool_call` / `done_when` ohne inhaltliche Aussage. Inhalt entsteht
erst mit `--include-findings`, und das erzwingt die Vollanalyse.

**Befund C — Der inhaltliche Pfad ist unbenutzbar langsam.** `--scope` schränkt laut Messung nur
die *Entscheidungslogik* ein, nicht die Analyse: eine Ein-Datei-Prüfung kostet 214–462 s, weil
Baseline und Ist jeweils vollständig analysiert werden.

**Schlussfolgerung:** Es existiert heute kein Pfad, der gleichzeitig schnell **und** inhaltlich ist.
Deshalb bringt drift in einer Claude-Code-Session nichts — unabhängig davon, wie gut die Signale sind.
Das ist die eigentliche Lücke, die dieses Vorhaben schließt.

---

## 4. Was gebaut wird

### 4.1 Das Produkt

Ein Claude-Code-Plugin `drift`, installierbar über das Plugin-Marketplace, mit **einer** Aufgabe:
den Agenten daran hindern, Struktur zu zerstören, **während** er editiert.

Die bestehende Engine (`src/drift/`) wird **nicht umgebaut**. Sie liefert offline den Index; sie ist
nie im heißen Pfad. Das ist die Scope-Grenze dieses Vorhabens.

### 4.2 Was der Nutzer sieht

```bash
/plugin marketplace add mick-gsk/drift
/plugin install drift@drift
```

Danach: nichts konfigurieren. Beim ersten Start baut drift im Hintergrund seinen Index; ab da wirkt
es in jeder Session.

**Oberfläche, hart begrenzt:**

| Element | Anzahl | Inhalt |
|---|---|---|
| MCP-Tools | **0** in v1 (Obergrenze 2) | Die Hooks liefern den Wert von selbst; ein Tool, das der Agent erst rufen muss, ist eine Bitte statt einer Wirkung. Erst bauen, wenn ein Nutzer es vermisst. |
| Slash-Commands | ≤ 2 | `/drift:doctor`, `/drift:stats` |
| Hooks | 4 | SessionStart, PreToolUse(Write\|Edit), PostToolUse(Write\|Edit), Stop |
| Konfigurationsdateien | 0 | keine `drift.yaml` nötig |

### 4.3 Architektur — drei Bausteine

```
                     offline / im Hintergrund
  ┌────────────────────────────────────────────────────────┐
  │  Baustein 2: Index-Builder                             │
  │  nutzt bestehende Engine (analyzer, arch_graph, signals)│
  │  schreibt .drift/index.db  (SQLite)                     │
  └────────────────────────────────────────────────────────┘
                              │
                              ▼  nur Lookups, keine Analyse
  ┌────────────────────────────────────────────────────────┐
  │  Baustein 1: drift.guard — schlanker heißer Pfad        │
  │  kein click / rich / networkx / pydantic / ML beim Import│
  │  Budget: p95 ≤ 150 ms kalt                              │
  └────────────────────────────────────────────────────────┘
                              │
                              ▼
  ┌────────────────────────────────────────────────────────┐
  │  Baustein 3: Claude-Code-Plugin                         │
  │  .claude-plugin/plugin.json + 4 Hooks + 2 Slash-Commands │
  └────────────────────────────────────────────────────────┘
```

**Baustein 1 — `drift.guard` (schlanker heißer Pfad).**
Ein neues Modul mit eigenem Entry-Point, das ausschließlich `sqlite3`, `ast`, `json`, `pathlib`
aus der Stdlib importiert. Kein `click`, kein `rich`, kein `networkx`, kein `pydantic`, nichts aus
`drift.cli` oder `drift.pipeline`. Es *liest* den Index und parst höchstens die eine geänderte Datei.
Begründung: die gemessenen 0,35 s Import-Kosten von `drift.cli` stammen zu ~0,30 s aus dem eager
Import aller 47 Command-Module — dieser Pfad darf sie nicht anfassen.

**Baustein 2 — `.drift/index.db` (SQLite).**
Vorberechnete Struktur, die Lookups in O(1) statt Analysen in O(Repo) erlaubt:

| Tabelle | Inhalt | Wofür |
|---|---|---|
| `symbols` | Datei, Symbolname, normalisierter Name, Signatur-Hash, Zeile | Duplikat-Kandidaten |
| `import_edges` | beobachtete Verzeichnis→Verzeichnis-Importkante mit Häufigkeit | Grenzverletzungen |
| `files` | Pfad, SHA-256, Indexzeitpunkt | inkrementelles Update, Staleness |
| `meta` | Schema-Version, Build-Zeit, Repo-Wurzel | Schemabruch, Frische |

**Grenzen werden beobachtet, nicht konfiguriert.** Der Index speichert, welche
Verzeichnis-zu-Verzeichnis-Importe im Repo *tatsächlich vorkommen*. Führt eine Änderung eine Kante
ein, die es bisher nie gab (z. B. erstmals `src/api/ → src/db/`), ist das die Meldung. Das braucht
keine `drift.yaml`, keine Regelpflege und ist deterministisch prüfbar — es ist die einfachste
Umsetzung, die das Versprechen einlöst.

Aufbau über die bestehende Engine (`arch_graph`, `signals`, `analyzer`) — einmalig, im Hintergrund,
danach inkrementell pro geänderter Datei. Stale-Index blockiert nie: er antwortet mit dem, was er hat,
und markiert sich als veraltet.

**Baustein 3 — Das Plugin.**
`.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` + Hook-Skripte. Die Hook-Skripte
rufen ausschließlich Baustein 1 auf.

### 4.4 Datenfluss — der Wert-Moment

**SessionStart** → prüft Index-Frische. Fehlt/veraltet → Bau im Hintergrund anstoßen, Session nicht
blockieren. Injiziert einen kurzen Satz Routing-Text (was drift ist, wann der Agent `drift_guard` ruft).

**PreToolUse(Write|Edit)** → greift **nur, wenn die Zieldatei noch nicht existiert**, der Agent also
gerade eine neue Datei anlegt. Genau dort entsteht Duplizierung, und genau dort ist der Hinweis
selten genug, um nicht zu nerven. Zwei Lookups gegen den Index:
1. *Nachbarschaft:* Welche Symbole liegen im Zielverzeichnis schon vor? → der Agent weiß, was da ist,
   bevor er etwas Zweites baut.
2. *Grenzen des Verzeichnisses:* Welche Importziele kommen aus diesem Verzeichnis vor? → „Dateien in
   `src/api/` importieren bisher nur aus `src/services/`."

Bei einer Änderung an einer **bestehenden** Datei sagt der Pre-Hook nichts — dafür ist der Post-Hook da.

Ergebnis: kompakter Text (Zielgröße ≤ 500 Zeichen) im Hook-Output. **Bei nichts zu sagen: nichts sagen.**
Stille ist der Normalfall, nicht das Versagen.

**PostToolUse(Write|Edit)** → nur die geänderte Datei parsen, ihre Symbole und Importe gegen den
Index diffen. Zwei Regeln:
1. *Duplikat:* neu hinzugekommenes Symbol, dessen normalisierter Name (oder Signatur-Hash) anderswo
   im Repo schon existiert → „`validate_token` existiert bereits in `src/auth/tokens.py:44`."
2. *Neue Grenzkante:* neuer Import, dessen Verzeichnis→Verzeichnis-Kante im Index nicht vorkommt →
   „Erster Import von `src/api/` nach `src/db/` im ganzen Repo."

Treffer → sofortige Rückmeldung an den Agenten, Zähler +1. Index inkrementell nachziehen.

*Lokale Konventionen („11 von 12 Dateien hier nutzen X") sind bewusst zurückgestellt — sie sind
Komfort, nicht das Kernversprechen.*

**Stop** → Session-Bilanz: „drift: 3 Duplizierungen verhindert · 1 Grenzverletzung gemeldet."

### 4.5 Was ausdrücklich NICHT gebaut wird

- Keine Änderung an den 30 Signalen, am Scoring, an `pipeline.py`.
- Kein Löschen bestehender CLI-Commands (der Nutzer hat „neue minimale Tür" gewählt — die Altlast
  wird nicht angefasst, nur nicht mehr in den Vordergrund gestellt).
- Kein Daemon, kein Socket, kein Server. SQLite reicht; `serve/` bleibt außen vor.
- Keine LLM-Aufrufe im heißen Pfad.
- Keine neue Laufzeit-Dependency. `sqlite3` und `ast` sind Stdlib.

### 4.6 Fehlerbehandlung

Der Guard darf **nie** den Agenten blockieren, wenn er selbst kaputt ist. Grundregel: jeder Hook
fängt alles, schreibt im Fehlerfall eine Zeile nach stderr und gibt Exit 0 mit leerem Output zurück.
Kein Index → still nichts sagen und Bau anstoßen. Timeout (Hard-Budget, siehe G1) → abbrechen,
nichts sagen. Ein defekter Guard ist unsichtbar, kein Störfaktor.

### 4.7 Teststrategie

- **Latenz-Gates** als ausführbares Skript, nicht als Behauptung (siehe §5).
- **Inhalts-Gates** gegen ein Fixture-Repo mit *bekannt* eingebauten Duplikaten und
  Grenzverletzungen: der Guard muss sie finden und darf auf sauberen Dateien schweigen.
  Das ist zugleich der erste deterministische Wirksamkeitsnachweis, den das Audit vermisst —
  auf der Ebene, auf der er ehrlich führbar ist (erkennt der Guard, was er zu erkennen behauptet),
  ohne die unbewiesene Behauptung „drift verbessert Architekturqualität" zu erneuern.
- **Import-Gate:** Test prüft nach `import drift.guard`, dass `sys.modules` keines von
  `transformers, sklearn, torch, networkx, rich, click, pydantic` enthält.
- **Oberflächen-Gate:** Test liest `plugin.json` und schlägt fehl bei > 2 MCP-Tools oder > 2 Slash-Commands.

---

## 5. Harte Gates — Definition of Done

Jedes Gate ist ein Kommando mit sichtbarem Output. Nicht bestanden = nicht fertig. Alle Gates laufen
in CI, damit sie nicht verrotten.

| # | Gate | Schwelle | Warum diese Zahl |
|---|---|---|---|
| **G1** | `drift guard --file X` Latenz, p95 über 50 Läufe, kaltes Prozess-Start | **≤ 150 ms** | Muss deutlich unter der 350 ms liegen, die heute schon der leere `drift --help` kostet; bei 2 Hooks pro Edit bleibt die spürbare Zusatzlast unter ~0,3 s |
| **G2** | Import-Hygiene im heißen Pfad | **0 Treffer** aus `{transformers, sklearn, torch, networkx, rich, click, pydantic}` | Befund A: genau diese Kette kostet heute 3,0 s |
| **G3** | Guard-Inhalt auf Fixture-Repo | **≥ 90 %** der eingebauten Duplikate/Grenzverletzungen gemeldet, **0** Meldungen auf den sauberen Kontrolldateien | Befund B: der heutige Vertrag ist zu 100 % leer; ein Guard, der schweigt, ist wertlos, einer der lärmt, wird abgeschaltet |
| **G4** | Oberfläche | **≤ 2** MCP-Tools, **≤ 2** Slash-Commands, **0** Pflicht-Konfigdateien | context-mode: 11 Tools für vier Teilprobleme; drift hat eines |
| **G5** | Install → Plugin aktiv und antwortend (`/drift:doctor` grün, Index-Bau im Hintergrund gestartet) | **≤ 60 s** auf sauberer Maschine, gemessen von Skript | Prinzip 4: null Entscheidungen; alles darüber verliert den Nutzer. *Der erste inhaltliche Guard-Treffer folgt, sobald der Index fertig ist — das ist G6, nicht G5.* |
| **G6** | Index-Bau auf Referenz-Repo (drift selbst, 344 Dateien) | **≤ 120 s** einmalig, **≤ 2 s** inkrementell pro Datei | Muss in einer Kaffeepause fertig sein, nicht in der Mittagspause (heute: 214–462 s pro Ein-Datei-Prüfung) |
| **G7** | Zähler-Ehrlichkeit | Zähler zählt nur Ereignisse, die ein Test als echt reproduziert | Das Audit fand vier verschiedene Selbst-Scores und einen hartkodierten „Bootstrap-Snapshot". Dieser Fehler darf sich nicht wiederholen |

**Baseline-Regel:** Vor Phase 1 werden die heutigen Werte mit demselben Skript gemessen und
eingecheckt. Jede spätere Zahl wird gegen diese Baseline berichtet — keine Zahl ohne Vergleich.

---

## 6. Risiken

| Risiko | Umgang |
|---|---|
| **Der Guard ist zu laut** und der Nutzer schaltet ihn ab (HN-Kritik an context-modes Hooks: *„The hooks seem too aggressive"* — hereme888) | G3 zwingt zu 0 Meldungen auf Kontrolldateien. Standard ist Schweigen. Warnen, nie blockieren. |
| **Der Guard ist zu leise** und niemand merkt, dass er läuft | Stop-Hook-Bilanz + `/drift:stats` machen auch „0 Funde" sichtbar. Der Nutzer soll wissen, dass geprüft wurde. |
| **Duplikat-Erkennung über Namen/Signatur ist zu grob** (FP auf `__init__`, `run`, `handle`) | Stoppwort-Liste häufiger Namen; Signatur-Hash zusätzlich zum Namen; Fixture-Korpus enthält bewusst solche Fälle. |
| **150 ms sind mit Python-Prozessstart nicht erreichbar** | Früh messen (Phase 0 misst den nackten `python -c "import sqlite3"`-Start als Untergrenze). Wenn die Untergrenze schon > 150 ms liegt, wird das Gate mit dokumentierter Begründung auf die gemessene Untergrenze + 50 ms angehoben — **nicht** stillschweigend gelockert. |
| **Der Index veraltet und meldet Falsches** | `meta`-Tabelle mit Datei-Hashes; PostToolUse zieht inkrementell nach; bei Schema-Bruch wird der Index verworfen und neu gebaut. |
| **Scope-Erosion** — aus dem Plugin wird wieder eine Feature-Sammlung | G4 als CI-Test. Neue Oberfläche erfordert das Entfernen anderer. |

---

## 7. Offene Punkte (bewusst nicht in diesem Vorhaben)

- Die vom Audit geforderte **Outcome-Validierung** (korreliert der drift-Score mit echten Defekten?)
  bleibt offen. Dieses Vorhaben umgeht sie bewusst: der Guard behauptet nicht, Architekturqualität zu
  verbessern, sondern nur, konkrete Duplikate und Grenzverletzungen zu melden — und das ist
  deterministisch prüfbar (G3).
- Die Reduktion der 47 CLI-Commands / 60 CI-Workflows bleibt liegen (Nutzerentscheidung: neue Tür
  statt Umbau). Sie wird durch dieses Vorhaben nicht schlimmer.
- Multi-Plattform (Cursor, Copilot, Codex) ist explizit später. Erst muss ein Kanal funktionieren.

---

## 8. Referenzen

- Messungen dieses Dokuments: reproduzierbar über das in Phase 0 einzucheckende Skript
  `scripts/gates/measure_baseline.py`.
- `AUDIT_2026-06-29.md` — 11-Dimensionen-Audit, Signal-Korrektheit und Sicherheit.
- `.drift-audit-report.md` — Over-Engineering-Befund, Surface-Drittelung, Wirksamkeitsfrage.
- context-mode: <https://github.com/mksglu/context-mode> · HN-Diskussion:
  <https://news.ycombinator.com/item?id=47193064>
