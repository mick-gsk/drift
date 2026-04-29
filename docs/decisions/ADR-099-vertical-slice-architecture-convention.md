---
id: ADR-099
status: proposed
date: 2026-04-28
supersedes:
---

# ADR-099: Vertical Slice Architecture als Konvention für neue Features und inkrementelle Migration

## Kontext

`src/drift/` ist heute ein hybrider modularer Monolith. Use-Case-Logik ist über drei
Eingabekanäle verteilt — [src/drift/commands/](../../src/drift/commands/) (~45 Verb-Module),
[src/drift/api/](../../src/drift/api/) (~25 Endpoint-Module) und die acht Bounded-Context-Router
[mcp_router_analysis.py](../../src/drift/mcp_router_analysis.py),
[mcp_router_session.py](../../src/drift/mcp_router_session.py),
[mcp_router_calibration.py](../../src/drift/mcp_router_calibration.py),
[mcp_router_intent.py](../../src/drift/mcp_router_intent.py),
[mcp_router_patch.py](../../src/drift/mcp_router_patch.py),
[mcp_router_repair.py](../../src/drift/mcp_router_repair.py),
[mcp_router_retrieval.py](../../src/drift/mcp_router_retrieval.py),
[mcp_router_architecture.py](../../src/drift/mcp_router_architecture.py).

Die MCP-Router sind **bereits feature-/use-case-shaped**, ohne dass diese Konvention
autoritativ dokumentiert wäre. Gleichzeitig sind `signals/`, `scoring/`, `output/`,
`ingestion/` und `models/` bewusst technisch geschichtet. [pipeline.py](../../src/drift/pipeline.py)
und [analyzer.py](../../src/drift/analyzer.py) sind zentrale Gatekeeper mit breitem Fan-In/-Out.

Folgen ohne explizite Konvention:

- Use-Case-Logik wächst dreifach pro neuem Eingabekanal statt einmal pro Slice.
- Top-Level-Module wie [recommendation_refiner.py](../../src/drift/recommendation_refiner.py),
  [suppression.py](../../src/drift/suppression.py),
  [trend_history.py](../../src/drift/trend_history.py),
  [outcome_tracker.py](../../src/drift/outcome_tracker.py),
  [finding_context.py](../../src/drift/finding_context.py),
  [finding_priority.py](../../src/drift/finding_priority.py),
  [finding_rendering.py](../../src/drift/finding_rendering.py),
  [fix_plan_dismissals.py](../../src/drift/fix_plan_dismissals.py)
  liegen ohne klares Ownership zwischen Slices.
- `pipeline.py`/`analyzer.py` sind potenzielle Magneten für jede neue Use-Case-Logik.

## Entscheidung

Drift adoptiert **Vertical Slice Architecture als Konvention** für **neue Features** und
für die **inkrementelle Migration** bestehender Use-Cases. Konkret:

1. **Neue Features werden ab ADR-Akzeptanz als Slices aufgebaut**, nicht über separate
   Edits in `commands/`, `api/` und `mcp_router_*`. Pro Slice gilt das gleiche interne Layout:
   - `contracts.py` — slice-lokale DTOs/Pydantic-Modelle
   - `handlers.py` (oder `<usecase>.py`) — Use-Case-Logik
   - `cli.py` — Click-Subcommand-Registrierung
   - `api.py` — Public API-Funktion
   - `mcp.py` — MCP-Router (entspricht heutigem `mcp_router_*.py`)
   - co-lokalisierte Tests (Co-Lokations-Strategie wird in einer eigenen Folge-Notiz
     festgelegt, siehe [work_artifacts/vsa_test_colocation_strategy.md](../../work_artifacts/vsa_test_colocation_strategy.md))
2. **Bestehende Features werden pilotiert** in der Reihenfolge:
   1. **`retrieval/`** (niedrigstes Risiko, bereits self-contained — siehe
      [work_artifacts/vsa_pilot1_retrieval_boundary_audit.md](../../work_artifacts/vsa_pilot1_retrieval_boundary_audit.md))
   2. **`intent/`**
   3. **`calibrate/`**
3. **Folgende Bereiche bleiben bewusst geschichtet** (Domain Core / Cross-Cutting):
   - [src/drift/signals/](../../src/drift/signals/), [src/drift/scoring/](../../src/drift/scoring/),
     [src/drift/ingestion/](../../src/drift/ingestion/), [src/drift/models/](../../src/drift/models/),
     [src/drift/output/](../../src/drift/output/) und [pipeline.py](../../src/drift/pipeline.py).
   - [src/drift/config/](../../src/drift/config/), [src/drift/errors/](../../src/drift/errors/),
     [telemetry.py](../../src/drift/telemetry.py), [cache.py](../../src/drift/cache.py),
     [types.py](../../src/drift/types.py), [signal_registry.py](../../src/drift/signal_registry.py).
4. **Slices dürfen Domain Core und Shared Infrastructure lesen, importieren aber keine
   anderen Slices.** Cross-Slice-Wiederverwendung erfolgt ausschließlich über Domain Core
   oder Shared.

### Was explizit **nicht** entschieden wird

- **Keine physische Verzeichnisumstellung** (kein `features/`-Verzeichnis) als Teil
  dieses ADR. Das Layout pro Slice greift, sobald ein Pilot tatsächlich migriert wird.
- **Keine Slicierung von `signals/`** entlang einzelner Signal-Klassen.
- **Kein Refactor von `pipeline.py` oder `analyzer.py`** als Voraussetzung für VSA.
- **Keine Breaking-Changes an `models/`** als Teil der Migration.
- **Keine vollständige Migration in einem Schritt.**

## Begründung

**Warum Vertical Slice statt klassischer Layered Architecture?**
Drift hat heute drei Eingabekanäle (CLI, Public API, MCP) für dieselben Use-Cases.
Layered Architecture multipliziert pro neuem Use-Case Aufwand und Drift-Risiko über
alle Kanäle. VSA bündelt einen Use-Case in einer Slice-Einheit und reduziert
Cross-Layer-Edits.

**Warum nicht radikale Neuordnung?**
Pipeline und Models sind heute zentral und tief verdrahtet. Ein Big-Bang würde
Audit-Pflichten (`audit_results/fmea_matrix.md`, `audit_results/risk_register.md`,
`audit_results/fault_trees.md`) gleichzeitig in mehreren Bereichen auslösen und
Precision/Recall-Tests destabilisieren. Inkrementelle Slice-Migration begrenzt den
Blast-Radius pro PR auf einen Use-Case.

**Warum `signals/` ausgeschlossen?**
Signale sind cross-cutting Domain Core und an `signal_registry.py`, `scoring/engine.py`,
[tests/fixtures/ground_truth.py](../../tests/fixtures/ground_truth.py) und Calibration
gebunden. POLICY §18 verlangt für Signaländerungen koordinierte Audit-Updates — eine
Slicierung würde diese Audit-Architektur fragmentieren.

**Verworfene Alternativen:**

- **Ports-and-Adapters / Hexagonal:** zu hoher Abstraktionsoverhead für aktuelle Drift-Größe;
  würde existierende MCP-Router-Pragmatik überformen.
- **Reines Modulkit ohne Konvention:** lässt die heutige Drift-Tendenz unverändert; jeder
  neue Use-Case erzeugt drei verteilte Edits.
- **Domain-driven Microservices:** widerspricht dem Single-Process-CLI-/MCP-Modell und
  Drift-Determinismus.

## Konsequenzen

**Akzeptierte Trade-offs:**

- Kleine, lokale Code-Dopplungen zwischen Slices sind **erlaubt**, solange sie
  klein und stabil sind. DRY ist nachrangig gegenüber klarer Slice-Grenze.
- Premature Abstraction wird ausdrücklich vermieden (Faustregel: 3+ stabile Vorkommen,
  bevor Extraktion in Domain Core / Shared erlaubt ist).
- Hybrider Zustand bleibt für längere Zeit erhalten — neuer Code folgt VSA, alter Code
  bleibt geschichtet, bis Pilots migriert sind.

**Folgepflichten:**

- Slice-Authoring-Skill muss verfügbar sein, bevor Pilot 1 migriert wird
  (siehe `.github/skills/drift-vertical-slice-authoring/SKILL.md`).
- Hidden-Feature-Modules ([recommendation_refiner.py](../../src/drift/recommendation_refiner.py)
  & Co.) müssen vor jeder Slice-Migration ein klares Zielhaus zugewiesen bekommen
  (Inventar: [work_artifacts/vsa_hidden_feature_modules_inventory.md](../../work_artifacts/vsa_hidden_feature_modules_inventory.md)).
- Test-Co-Lokations-Strategie muss vor Pilot 1 entschieden sein.
- Diese Entscheidung berührt **keine** Signale, Scoring-Logik, Output-Verträge oder
  Trust-Boundaries → POLICY §18-Audit-Pflichten werden durch dieses ADR **nicht** ausgelöst.
  Audit-Pflichten greifen erst, falls eine spätere Slice-Migration tatsächlich Domain Core
  berührt.

## Validierung

Die Entscheidung gilt als **bestätigt**, wenn nach Abschluss von Pilot 1 (`retrieval/`):

- Slice-Layout (`contracts.py`, `handlers.py`, `cli.py`, `api.py`, `mcp.py`) reproduzierbar
  durch das Authoring-Skill erzeugt wurde.
- Bestehende Tests für Retrieval (`tests/test_retrieval_corpus.py`,
  `tests/test_retrieval_search.py`, `tests/test_mcp_retrieval_tools.py`) **ohne Anpassung
  am Verhalten** weiter laufen.
- Boundary-Audit zeigt: keine zusätzlichen Imports von anderen Slices in den migrierten Code,
  Cross-Imports nur Richtung Domain Core / Shared.
- Pre-Push-Gates (`make gate-check`, Risk-Audit-Diff bei Bedarf) ohne neue Funde.

Konkrete Validierungsbefehle:

```bash
pytest tests/test_retrieval_corpus.py tests/test_retrieval_search.py tests/test_mcp_retrieval_tools.py -v
make check
make gate-check COMMIT_TYPE=chore
drift analyze --repo . --format json --exit-zero
```

Die Entscheidung gilt als **widerlegt**, wenn:

- Pilot 1 erzwingt, dass `models/`, `pipeline.py` oder `signals/` material angefasst werden
  müssen, ohne dass dies auf einen ADR-konformen Domain-Core-Defekt zurückzuführen ist.
- Mehr als zwei Slices nach Migration gegenseitig importieren müssen.

Lernzyklus-Ergebnis: zunächst **unklar**; finale Bewertung nach Abschluss Pilot 1.

## Referenzen

- `POLICY.md` (insbesondere §6, §8, §13, §18)
- `.github/instructions/drift-policy.instructions.md`
- `.github/instructions/drift-quality-workflow.instructions.md`
- [.github/skills/drift-vertical-slice-authoring/SKILL.md](../../.github/skills/drift-vertical-slice-authoring/SKILL.md)
- [work_artifacts/vsa_pilot1_retrieval_boundary_audit.md](../../work_artifacts/vsa_pilot1_retrieval_boundary_audit.md)
- [work_artifacts/vsa_hidden_feature_modules_inventory.md](../../work_artifacts/vsa_hidden_feature_modules_inventory.md)
- [work_artifacts/vsa_test_colocation_strategy.md](../../work_artifacts/vsa_test_colocation_strategy.md)
