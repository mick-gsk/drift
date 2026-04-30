---
id: ADR-100
status: proposed
date: 2026-04-30
supersedes:
---

# ADR-100: Just-in-Time Context Injection für Agent-Workflows

## Kontext

Drift-Agents laden bisher `llms.txt` als undifferenzierte Discovery-Datei in vollem
Umfang. `llms.txt` enthält alle 25 Signale, Scoring-Metadaten, Release-Status und
allgemeine Use-Case-Beschreibungen — unabhängig davon, welche Signale im aktuellen
Lauf tatsächlich gefunden wurden. Bei einem Lauf mit drei Findings aus
`architecture_violation` werden damit auch zwanzig weitere Signaldokumentationen
und unverbundene ADR-Inhalte in den Kontext geladen, die für diesen Lauf keinen
Informationswert haben.

Bisherige Mechanismen:

- `scripts/_context_mapping.py` enthält `CONTEXT_PATHS` (task-type-basiertes Routing)
  für `feat`, `fix`, `chore`, `signal`, `prompt`, `review` — diese Dimension adressiert
  den Task-Typ des Entwicklers, nicht die Findings eines konkreten Laufs.
- `llms.txt` und vollständige ADR-Sammlung werden per Agent-Kontext pauschal
  injiziert, ohne Lauf-Selektivität.
- `action.yml` emittiert bisher keine signal-spezifischen Kontext-Hinweise.

Folge: Agents erhalten bei jedem Lauf einen breiten Kontext-Fußabdruck — selbst
wenn das Lauf-Ergebnis drei oder weniger Signale enthält. Das verbraucht
unnötig Context-Budget, verdünnt die relevante Dokumentation und erhöht das
Rauschen für den Agent.

## Entscheidung

Drift führt **Just-in-Time (JIT) Context Injection** ein: ein leichtgewichtiger
Manifest-Mechanismus, der zu einem `drift analyze`-Lauf die *minimale* Menge
relevanter Dokumentations-Pfade bestimmt und diese als strukturierten Output
(`context-hints`) für nachgelagerte Agent-Schritte verfügbar macht.

### Komponenten

#### 1. Signal-Kontext-Manifest (`scripts/_context_mapping.py`)

Neu: `SIGNAL_CONTEXT_PATHS` — ein dict, das Signal-IDs (lowercase, entspricht
`SignalType`-Enum-Werten) auf ein Tupel workspace-relativer Pfade abbildet.

- Budget: `MAX_PATHS_PER_SIGNAL = 4` Pfade pro Signal.
- Pflichtinhalt pro Signal: mindestens die Signal-Referenz-Doku
  (`docs-site/reference/signals/<code>.md`).
- ADRs werden nur eingetragen, wenn sie Präzisions- oder Design-Entscheidungen
  enthalten, die nicht aus dem Signal-Doc allein hervorgehen.
- Nicht gemappte Signale geben ein leeres Tupel zurück (kein Raise) — safe to iterate.

#### 2. JIT Injection Helper (`scripts/get_context_hints.py`)

- Liest einen Drift-JSON-Report, extrahiert die eindeutigen Signal-IDs in Score-Reihenfolge.
- Dedupliziert Pfade über Signal-Grenzen hinweg.
- Cappiert Ausgabe auf `MAX_TOTAL_PATHS = 12` Pfade.
- Fehlerverhalten: silent bei fehlendem / ungültigem Report (`[]`); Log auf stderr
  bei unerwartetem I/O-Fehler.

#### 3. CI-Validator (`scripts/validate_context_manifest.py`)

- Prüft, ob alle referenzierten Pfade im Workspace existieren.
- Stellt sicher: mindestens 20 Signale mit dediziertem Mapping (Gate gegen
  versehentliches Kürzen der Mapping-Tabelle).
- Stellt sicher: kein Signal überschreitet `MAX_PATHS_PER_SIGNAL`.
- Integriert in `ci.yml` Job `version-check` als eigener Step.

#### 4. GitHub Action Output (`action.yml`)

- Neuer Output `context-hints`: newline-separierte workspace-relative Pfade für
  die Signale im aktuellen Lauf.
- Neuer Step `Inject signal context hints` ruft `get_context_hints.py` auf dem
  JSON-Report auf und schreibt das Ergebnis in `$GITHUB_OUTPUT`.

### Budget-Entscheidungen

| Dimension | Wert | Begründung |
|---|---|---|
| `MAX_PATHS_PER_SIGNAL` | 4 | Signal-Doc + bis zu 3 design-relevante ADRs — ausreichend, ohne Context-Budget zu erschöpfen |
| `MAX_TOTAL_PATHS` | 12 | Entspricht ~3 Signals à 4 Pfade; deckt typische Drift-Läufe mit 1–5 signifikanten Findings |
| `MIN_MAPPED_SIGNALS` (CI-Gate) | 20 | Schützt vor versehentlichem Kürzen des Manifests unter die produktive Mapping-Tiefe |

### Abgrenzung zu bestehenden Mechanismen

| Mechanismus | Dimension | Selektivität |
|---|---|---|
| `llms.txt` | Gesamt-Discovery | Keine — pauschal |
| `CONTEXT_PATHS` (task-type) | Developer-Task-Typ | Nach Task-Typ, nicht nach Findings |
| `SIGNAL_CONTEXT_PATHS` (dieses ADR) | Lauf-spezifisch | Nach tatsächlichen Findings |

Die drei Mechanismen schließen sich nicht aus: Task-Typ-Routing und JIT Injection
können kombiniert werden. `llms.txt` bleibt als vollständige Discovery-Oberfläche
für Konsumenten, die keinen selektiven Einstieg benötigen.

## Begründung

**Warum JIT statt full `llms.txt`?**
Bei einem konkreten Lauf mit 3–5 Findings aus bekannten Signal-Typen ist der
volle `llms.txt`-Kontext um Faktor 5–10 überdimensioniert. JIT injection reduziert
den Kontext-Fußabdruck auf den minimal notwendigen Slice und verbessert damit
Signal-zu-Rauschen-Verhältnis für nachgelagerte Agents.

**Warum `MAX_PATHS_PER_SIGNAL = 4`?**
Jedes Signal hat eine Referenz-Doku und optional 1–3 ADRs mit Design-Entscheidungen.
Mehr als 4 Pfade pro Signal würden auf Wiederholung oder On-Topic-Verlust hindeuten.
Der Wert ist konservativ und kann per ADR-Update erhöht werden.

**Warum `MAX_TOTAL_PATHS = 12`?**
12 Pfade entsprechen bei 4 Pfaden/Signal drei vollständig aufgelösten Signals —
ein realistisches Upper-Bound für einen handlungsrelevanten Lauf. Bei mehr als
drei dominanten Signals degeneriert der Kontext-Gewinn pro weiterem Pfad.

**Warum CI-Gate mit `MIN_MAPPED_SIGNALS = 20` statt 3?**
Mit 24 gemappten Signalen zum Zeitpunkt der Einführung wäre ein Wert von 3
wirkungslos gegen versehentliche Kürzungen. 20 reflektiert den tatsächlichen
Produktivumfang und schlägt Alarm, bevor eine signifikante Mapping-Lücke
unbemerkt auf `main` landet.

**Verworfene Alternativen:**

- **Vollständiger ADR-Dump pro Signal:** Zu groß; viele ADRs betreffen
  Infrastruktur-Entscheidungen (Output-Format, CLI-Flags), die für eine
  Fixing-Session nicht relevant sind.
- **Kein Mechanism (Agent wählt selbst):** Nicht deterministisch; erzeugt
  ungleiche Lauf-zu-Lauf-Kontext-Budgets ohne Audit-Spur.
- **llms.txt Sectioning (Abschnitte pro Signal):** Würde `llms.txt` als
  Discovery-Oberfläche mit eingebetteter Präzisions-Doku vermischen und die
  Trennung von Discovery- und Fixing-Kontext aufheben.

## Konsequenzen

**Positiv:**
- Agents erhalten pro Lauf einen minimalen, fokussierten Kontext-Slice.
- CI-Gate schützt das Manifest gegen Regression.
- Kein Breaking Change an `llms.txt` oder bestehenden Kontext-Mechanismen.
- Zero-Path-Ausgabe bei leerem Lauf (keine Findings → keine Injection) ist explizit
  sicheres Verhalten.

**Negativ / Trade-offs:**
- Manifest muss bei neuen Signalen manuell erweitert werden (nicht auto-generiert).
  Mitigation: CI-Gate schlägt bei neuen Signalen ohne Mapping nicht an — das ist
  bewusst toleriert, da ein neues Signal zunächst kein dediziertes Mapping braucht.
- `get_context_hints.py` ist ein optionaler Schritt in `action.yml` — Nutzer, die
  das Output nicht konsumieren, erhalten keinen Mehrwert.

**Nicht im Scope dieses ADR:**
- Automatische Generierung des Manifests aus `signal_registry`.
- Integration in MCP-Tools (Folge-ADR bei Bedarf).
- Kontextpfade für nicht-Python-Signale (`ts_architecture`, `type_safety_bypass`).

## Validierung

Die Entscheidung gilt als bestätigt, wenn:

- `python scripts/validate_context_manifest.py` → exit 0 mit ≥ 20 gemappten Signalen.
- `python scripts/get_context_hints.py <json-report>` gibt auf einem realen Lauf
  ≤ 12 Pfade zurück und alle Pfade existieren im Workspace.
- CI `version-check` Job läuft grün.
- `action.yml` Output `context-hints` ist in Downstream-Workflows konsumierbar.

```bash
python scripts/validate_context_manifest.py
python scripts/get_context_hints.py benchmark_results/latest.json
pytest tests/test_get_context_hints.py tests/test_context_manifest.py -v
```

## Referenzen

- `POLICY.md` §8 (Feature-Gates), §13 (Finding-Qualität)
- `.github/instructions/drift-policy.instructions.md`
- `.github/instructions/drift-push-gates.instructions.md`
- [ADR-092: llms.txt deterministisch generieren](ADR-092-llms-txt-autogen.md)
- [ADR-031: Agent Context Layer](ADR-031-agent-context-layer.md)
- `scripts/_context_mapping.py`
- `scripts/get_context_hints.py`
- `scripts/validate_context_manifest.py`
- `action.yml`
