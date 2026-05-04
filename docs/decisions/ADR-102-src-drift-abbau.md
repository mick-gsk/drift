---
id: ADR-102
status: proposed
date: 2026-05-01
supersedes: []
---

# ADR-102: Vollständiger Abbau von `src/drift/`

## Kontext

ADR-100 hat das uv-Workspace-Monorepo mit physisch getrennten Capability-Paketen unter
`packages/` aufgebaut und `src/drift/` in einen reinen Backward-Compat-Layer umgewandelt.
Dieser Layer ist technisch notwendig, solange:

1. **2 473 Test-Imports** auf `from drift.X` / `import drift.X` zeigen (Stand: 2026-05-01).
2. **Python `import drift` löst auf `src/drift/__init__.py`** auf — nicht auf
   `packages/drift/src/drift/`, weil das Root-`pyproject.toml` den Hatch-Build auf
   `src/drift` verweist und das `packages/drift`-Paket vom uv-Workspace
   (`exclude = ["packages/drift"]`) ausgeschlossen ist.
3. **`src/drift/` enthält noch 45 Root-Dateien mit echtem Code** (kein `sys.modules`-Stub),
   darunter `analyzer.py`, `pipeline.py`, `types.py`, `signal_registry.py` u.a.,
   die noch in kein Capability-Paket migriert wurden.
4. **12 Unterordner mit echtem Code** sind noch nicht extrahiert:
   `api`, `arch_graph`, `blast_radius`, `calibration`, `drift_kit`, `errors`,
   `integrations`, `intent`, `lang`, `negative_context`, `patch_writer`, `pr_loop`,
   `retrieval`, `self_improvement`, `serve`, `synthesizer`, `verify`.

Der Abbau ist in ADR-100 als Folgepflicht benannt, aber bewusst zurückgestellt worden.
Diese ADR definiert den vollständigen Abbau-Pfad als eigenständige Entscheidung.

## Entscheidung

`src/drift/` wird vollständig abgebaut. Das `drift`-Namespace wird danach ausschließlich
durch `packages/drift/src/drift/` (Meta-Paket) bedient. Der Abbau erfolgt in drei Phasen:

### Phase A — Noch fehlende Capability-Pakete extrahieren

Die 45 unmigrierte Root-Dateien und 17 unmigrierte Unterordner werden auf bestehende
oder neue Capability-Pakete verteilt:

| Datei / Ordner | Ziel-Paket | Begründung |
|---|---|---|
| `analyzer.py`, `pipeline.py`, `signal_registry.py`, `signal_mapping.py`, `incremental.py`, `baseline.py`, `cache.py`, `precision.py`, `profiles.py` | `drift-engine` | Engine-Schicht: Analyse-Pipeline, Signal-Registry |
| `types.py` | `drift-sdk` | Bereits als Re-export vorhanden; echter Code noch in `src/drift/types.py` |
| `api/` | `drift-sdk` | ADR-100 §Phase-2-Scope: `api/` war bewusst zurückgestellt |
| `errors/` | `drift-sdk` | Cross-Layer-Fehlertypen |
| `models/` (Re-export) | vollständig in `drift-sdk` | Bereits migriert, nur Stub übrig |
| `finding_rendering.py`, `recommendations.py`, `recommendation_refiner.py` | `drift-output` | Output-Schicht |
| `output/` (Stub) | wird zu echtem Re-export in Meta-Paket | |
| `arch_graph/`, `calibration/`, `blast_radius/`, `retrieval/`, `negative_context/` | `drift-engine` | Analyse-Hilfsdienste |
| `patch_writer/`, `intent/`, `synthesizer/`, `self_improvement/` | `drift-engine` | Fix/Repair-Schicht |
| `pr_loop/`, `serve/` | `drift-mcp` | MCP-Runtime-Dienste |
| `drift_kit/` | `drift-cli` | Kit-Scaffolding-Kommandos |
| `integrations/`, `lang/`, `verify/` | `drift-engine` | Sprachanalyse, Verifikation |
| `task_graph.py`, `task_spec.py`, `next_step_contract.py`, `repair_template_registry.py` | `drift-session` | Session-/Task-Schicht |
| `telemetry.py`, `plugins.py`, `suppression.py`, `guardrails.py`, `preflight.py`, `ci_detect.py` | `drift-engine` | Querschnitts-Infrastruktur |
| `scope_resolver.py`, `context_tags.py`, `copilot_context.py`, `response_shaping.py`, `situational_hints.py` | `drift-session` | Kontext-/Scope-Auflösung |
| `policy_compiler.py`, `fix_plan_dismissals.py`, `fix_intent.py` | `drift-engine` | Policy/Fix-Plan |
| `adr_scanner.py` | `drift-engine` | ADR-Erkennung |
| `api_helpers.py`, `tool_metadata.py`, `attribution.py`, `logical_location.py` | `drift-sdk` | API-Hilfsfunktionen |
| `embeddings.py` | `drift-engine` | Retrieval/Embedding |
| `finding_context.py`, `finding_priority.py` | `drift-output` | Finding-Anreicherung |
| `quality_gate.py`, `remediation_activity.py` | `drift-session` | Gate/Remediation |
| `timeline.py`, `trend_history.py` | `drift-session` | Zeitreihen |

### Phase B — `packages/drift/src/drift/` als vollständiger Namespace ausbauen

Das Meta-Paket `packages/drift/src/drift/` erhält die vollständigen Sub-Package-Stubs
(Ordner + `__init__.py`) für alle `drift.*`-Namespaces, die bisher in `src/drift/`-Stubs
leben:

- `drift.signals`, `drift.config`, `drift.commands`, `drift.ingestion`, `drift.models`,
  `drift.output`, `drift.scoring`, `drift.session`, `drift.api`, usw.

Diese Stubs sind schlank: nur `from <capability_pkg>.<modul> import *` oder
explizite `from … import X as X`-Zeilen für mypy-Sichtbarkeit.

### Phase C — Build-Pivot und `src/drift/` löschen

1. Root-`pyproject.toml`: `[tool.hatch.build.targets.wheel] packages = ["src/drift"]`
   → `packages = ["packages/drift/src/drift"]` (oder Build-Delegation an `packages/drift`).
2. `pyproject.toml` `[tool.uv.workspace]`: `exclude = ["packages/drift"]` entfernen,
   `packages/drift` wird reguläres Workspace-Member.
3. `[tool.uv.sources]` im Root: `drift = { workspace = true }` ergänzen.
4. Coverage, mypy, pytest `testpaths`, `paths_to_mutate` auf `packages/**` umstellen.
5. `src/drift/` vollständig löschen.
6. CI-Pfadfilter `src/drift/**` entfernen (Phase 6b hat `packages/**` bereits hinzugefügt).

### Was explizit **nicht** entschieden wird

- Keine Änderung der Test-Import-Pfade (`from drift.X`). Tests importieren weiterhin
  via `drift.*` — das Meta-Paket stellt diese Compat-Imports weiterhin bereit.
- Keine Änderung der Public-API-Versprechen oder PyPI-Distributionsstrategie.
- Keine Zerlegung von `drift-engine` in feinere Pakete (ADR-099 §3 bleibt gültig).

## Begründung

**Warum jetzt eine eigene ADR statt weiterer ADR-100-Phasen?**
ADR-100 hat seinen Scope erfüllt (alle Capability-Pakete extrahiert). Der Abbau von
`src/drift/` ist eine qualitativ andere Entscheidung: er berührt den Build-Pivot,
Test-Infrastruktur und den Lösch-Akt des Quellordners. Ein eigenes ADR erlaubt präzisere
Validierungskriterien und einen eigenständigen Rollback-Pfad.

**Warum die Test-Imports nicht migrieren?**
2 473 `from drift.X`-Imports manuell umzuschreiben hat hohes Fehlerrisiko und keinen
messbaren Nutzen für die eigentliche Ziel-Eigenschaft (Agent-Kontext-Reduktion). Das
Meta-Paket-Re-export hält sie stabil. Eine spätere Code-Mod-Migration ist optional.

**Warum Phase A vor Phase C?**
Solange echter Code in `src/drift/` liegt (45 Root-Dateien + 17 Unterordner), wäre
das Löschen destruktiv. Die Reihenfolge A → B → C stellt sicher, dass in Phase C
keine Fachlogik verloren geht.

## Konsequenzen

- Nach Phase C ist `src/drift/` kein Pfad mehr im Repo — CI-Guards, Agenten und
  Guard-Skills müssen auf `packages/drift-*/` zeigen (Phase 7a im ADR-100 bleibt
  als Vorbedingung für Phase C relevant).
- `pip install -e .` funktioniert weiterhin, weil der Root `pyproject.toml` auf
  `packages/drift` delegiert.
- `drift --version` und alle bestehenden `from drift.X import Y`-Imports in Tests
  bleiben ohne Änderung funktional.
- Blast-Radius: betrifft Build-Config, CI-Path-Filter, Coverage-Config, mypy-Pfade,
  vulture-Pfade, mutation-Benchmark-Pfade. Kein Signal-/Scoring-/Output-Vertrags-
  änderung → keine Audit-Artefakt-Pflicht nach POLICY §18.

## Validierung

Die Entscheidung gilt als **umgesetzt**, wenn:

1. `src/drift/` existiert nicht mehr im Repo.
2. `python -c "import drift; print(drift.__file__)"` zeigt auf
   `packages/drift/src/drift/__init__.py`.
3. `drift --version` gibt die korrekte Version aus.
4. `make check` (lint + typecheck + pytest + self-analysis) vollständig grün.
5. `from drift.signals.architecture_violation import ArchitectureViolationSignal` in
   einem frischen Python-Prozess auflösbar (Compat-Layer funktional).
6. `uv sync` im Workspace-Root ohne Fehler.

### Phasen-spezifische Zusatz-Gates

| Phase | Zusatz-Gate |
|-------|-------------|
| A | Jede migrierte Datei/Ordner: Unittest-Suite der Ziel-Capability grün; kein Import-Fehler in `from drift.X`-Callsites |
| B | Alle `drift.*`-Namespaces über Meta-Paket-Stubs erreichbar; mypy sieht alle exportierten Symbole |
| C | `src/drift/` gelöscht; Build-Pivot grün; `make check` vollständig grün |

### Rollback-Regel

Wenn Phase A ungeplante Kopplungen aufdeckt (z.B. zirkuläre Abhängigkeiten zwischen
noch unmigriertem Code und Capability-Paketen), wird Phase A für das betroffene Modul
eingefroren und eine ADR-102-Neubewertung gestartet, bevor Phase B oder C fortgesetzt wird.
