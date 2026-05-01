---
id: ADR-100
status: proposed
date: 2026-05-01
supersedes: []
---

# ADR-100: uv Workspace Monorepo mit physischen Capability-Paketen

## Kontext

ADR-099 hat VSA als **Konvention** innerhalb des bestehenden `src/drift/`-Layouts eingeführt
und physische Verzeichnisumstellungen bewusst ausgeschlossen. Der verbleibende Hauptreibungspunkt
ist ein anderer: Coding-Agenten laden beim Bearbeiten einer Aufgabe (z.B. "fix MCP routing")
den gesamten `src/drift/`-Kontext (80+ Dateien, 343 Module) und können den für die Aufgabe
relevanten Code nicht von anderen Capabilities abgrenzen.

ADR-100 **ergänzt** ADR-099 (insbesondere die dort gesetzten Grenzen zur Signal-Slicierung)
und ersetzt ADR-099 nicht.

Das führt zu:
- Übermäßigem Kontext-Blast bei Agent-Tasks (kein klares Scope-Signal)
- Agent-Guards müssen auf Dateiebene gewartet werden statt auf Paketebene zu stehen
- `make test-for FILE=src/drift/mcp_server.py` läuft immer die volle Suite ohne natürliche
  Test-Scope-Grenze

Grundlage: Circular-Import-Analyse (2026-05-01) ergab **keine zirkulären Abhängigkeiten**
in `src/drift/` — die physische Trennung ist damit ohne vorherige Entkopplungsarbeit möglich.

## Entscheidung

Drift migriert schrittweise zu einem **uv Workspace Monorepo** mit physisch getrennten
Capability-Paketen unter `packages/`. Build-Backend bleibt hatchling je Paket.
PyPI-Distribution erfolgt weiterhin ausschließlich über das Meta-Paket `drift-analyzer`.
Die Slice-Pakete werden **nicht** eigenständig auf PyPI released.

### Zielstruktur

```
drift/                              # Workspace-Root
├── pyproject.toml                  # [tool.uv.workspace] members=["packages/*"]
├── uv.lock                         # workspace-weites Lockfile (ersetzt Root-Lockfile)
├── packages/
│   ├── drift-config/               # config/, profiles.py, rules/
│   │   ├── pyproject.toml          # hatchling, no upstream deps
│   │   ├── src/drift_config/
│   │   └── tests/
│   ├── drift-sdk/                  # api/, types.py, models/
│   │   ├── pyproject.toml          # depends: drift-config
│   │   ├── src/drift_sdk/
│   │   └── tests/
│   ├── drift-engine/               # signals/, scoring/, ingestion/, pipeline.py, analyzer.py
│   │   ├── pyproject.toml          # depends: drift-sdk, drift-config
│   │   ├── src/drift_engine/
│   │   └── tests/
│   ├── drift-output/               # output/, finding_rendering.py, recommendations.py
│   │   ├── pyproject.toml          # depends: drift-sdk
│   │   ├── src/drift_output/
│   │   └── tests/
│   ├── drift-session/              # session.py, session_*.py, outcome_*/, reward_chain.py
│   │   ├── pyproject.toml          # depends: drift-engine, drift-output
│   │   ├── src/drift_session/
│   │   └── tests/
│   ├── drift-mcp/                  # mcp_server.py, mcp_router_*.py, mcp_orchestration.py
│   │   ├── pyproject.toml          # depends: drift-engine, drift-session, drift-output
│   │   ├── src/drift_mcp/
│   │   └── tests/
│   ├── drift-cli/                  # commands/, cli.py
│   │   ├── pyproject.toml          # depends: alle slice packages
│   │   ├── src/drift_cli/
│   │   └── tests/
│   └── drift/                      # Meta-Paket (PyPI: drift-analyzer)
│       ├── pyproject.toml          # aggregiert alle packages, entry-points hier
│       └── src/drift/              # re-exportiert Public API für Backward-Compat
├── tests/                          # Integration-Tests (cross-slice, unveränderter Pfad)
└── extensions/vscode-drift/        # unverändert
```

### Dependency-DAG (strikt leftward, kein Cross-Slice-Import)

```
drift-config
└── drift-sdk
  ├── drift-engine
  │   └── drift-session
  │       └── drift-mcp
  └── drift-output
    ├── drift-session
    └── drift-mcp

drift-cli
├── drift-config
├── drift-sdk
├── drift-engine
├── drift-output
├── drift-session
└── drift-mcp

drift (meta)
└── drift-cli
```

### Migrationsstrategie (iterativ, Phase für Phase)

Jede Phase ist ein eigenständiger PR. CI muss nach jeder Phase grün bleiben.
Backward-Compat wird durch das Meta-Paket-Re-export sichergestellt — bestehende
`from drift.X import Y`-Imports in `tests/` und Consumers müssen nicht sofort geändert werden.

**Scope-Abgrenzung `drift-sdk` (Phase 2):**
`drift-sdk` enthält `types.py` und `models/` (7 Untermodule: `_enums`, `_git`,
`_parse`, `_patch`, `_policy`, `_context`, `_agent`, `_findings`).
`api/` wird **nicht** in Phase 2 migriert: Die `api/`-Module haben Runtime-Imports auf
`drift.analyzer` (Engine-Layer) — eine Migration würde Kreisabhängigkeiten erzeugen.
`api/` wandert in Phase 3 zusammen mit `drift-engine`.

| Phase | Inhalt | Voraussetzung |
|-------|--------|---------------|
| 0 | ADR anlegen, Circular-Import-Analyse, feat-start | keine |
| 1 | uv Workspace Root + `drift-config` extrahieren | Phase 0 |
| 2 | `drift-sdk` extrahieren (`types.py`, `models/`) | Phase 1 |
| 3 | `drift-engine` extrahieren | Phase 2 |
| 4a | `drift-output` extrahieren | Phase 3 |
| 4b | `drift-session` extrahieren | Phase 4a |
| 5a | `drift-mcp` extrahieren | Phase 4b |
| 5b | `drift-cli` extrahieren | Phase 5a |
| 6a | Meta-Paket (`packages/drift`) + Re-export-Stubs | Phase 5b |
| 6b | Workflow- und Path-Filter-Migration (`src/drift/**` -> `packages/**`) | Phase 6a |
| 6c | Docs/Guard-Skills/Cleanup (u.a. `DEVELOPER.md`, Guard-Pfade) | Phase 6b |

### Was explizit **nicht** entschieden wird

- Keine eigenständigen PyPI-Releases der Slice-Pakete.
- Kein Wechsel von hatchling zu einem anderen Build-Backend.
- Keine Änderungen an Signal-/Scoring-/Output-Logik als Teil der Migration.
- Keine Änderung der Import-Pfade in `tests/` bis Phase 6 (Meta-Paket-Re-export hält sie valide).
- Keine Slicierung von `signals/` entlang einzelner Signal-Klassen (ADR-099 §3 bleibt gültig).

### Meta-Paket-Grenze (`packages/drift/src/drift/`)

`packages/drift/src/drift/` ist in dieser Migration ein **reiner Kompatibilitäts-Layer**:

- erlaubt sind Re-export-Stubs, Entry-Point-Bindings und dünne Import-Weiterleitungen
- nicht erlaubt ist neue produktive Fachlogik im Meta-Paket

Damit bleibt die Suchfläche für `drift.*` eindeutig: produktive Logik lebt in Slice-Paketen,
das Meta-Paket hält nur Backward-Compat.

## Begründung

**Warum physische Pakete statt nur logische Guards?**
Logische Guards (`.github/skills/guard-src-drift-mcp/`) müssen manuell mit dem Code synchron
gehalten werden. Ein physisches Paket ist eine klare, unveränderliche Scope-Grenze, die
jeder Agent sofort aus dem Dateisystem ablesen kann ohne Guard-Dateien zu kennen.

**Warum uv Workspaces?**
Das Repo nutzt bereits `uv.lock` und `uv sync`. uv Workspaces sind die native Erweiterung
ohne Build-Backend-Wechsel. Alternativ wäre `pip` editable installs möglich, aber ohne
Workspace-weites Lockfile-Management.

**Warum Meta-Paket statt direkter Import-Pfad-Migration?**
300+ Testdateien importieren `from drift.X`. Eine sofortige Migration würde alle PRs
blockieren. Das Meta-Paket-Re-export entkoppelt Migrations-Timeline von Test-Stabilität.

**Warum bleibt `drift-engine` zunächst breit?**
`signals/`, `scoring/`, `ingestion/`, `pipeline.py` und `analyzer.py` werden bewusst zusammen
verschoben, um zuerst die Capability-Grenze gegenüber Session/MCP/CLI zu stabilisieren.
Eine feinere Zerlegung innerhalb von `drift-engine` ist als Folgeentscheidung möglich,
aber nicht Teil dieser ADR (ADR-099 §3 bleibt maßgeblich).

**Verworfene Alternativen:**

- **Nur logische Guards ohne physische Trennung:** Scope-Signal bleibt schwach; Agenten
  müssen Guard-Dateien kennen und befolgen.
- **Eigenständige PyPI-Releases der Slice-Pakete:** Erhöht Release-Komplexität massiv
  ohne messbaren Nutzen für das Haupt-Use-Case (Agenten-Kontext-Reduktion).
- **Domain-driven Microservices:** widerspricht Single-Process-CLI-/MCP-Modell (ADR-099).

## Konsequenzen

**Akzeptierte Trade-offs:**

- Workspace-Root `pyproject.toml` verliert `[project]`-Sektion nach Phase 6 — das
  Root-Paket ist dann kein installierbares Paket mehr, nur Workspace-Koordinator.
- 50+ GitHub Workflows müssen in Phase 6b `src/drift/**` → `packages/**` path-filter
  aktualisieren.
- `hatch build` muss für das Meta-Paket in `packages/drift/` aufgerufen werden (nicht Root).
- Migration POLICY §18: betrifft keine Signale/Scoring/Output-Verträge/Trust-Boundaries →
  keine Audit-Artefakt-Pflicht durch dieses ADR selbst. Audit-Pflichten greifen wenn
  einzelne Slice-Migrationen Domain Core berühren (insbesondere Phase 3: drift-engine).

**Folgepflichten:**

- Guard-Skills in `.github/skills/guard-src-drift-*/` müssen nach Phase 6c auf neue
  Pfade `packages/drift-*/` aktualisiert werden.
- `DEVELOPER.md` muss nach Phase 6c auf workspace-weite `uv sync`-Anleitung umgestellt werden.
- `drift.schema.json`-Konsistenztest (ADR via tests/test_config_schema.py) bleibt unverändert
  gültig — liegt im Meta-Paket.

### Rollback- und Replan-Regel

Wenn eine Phase ungeplante Kopplungen aufdeckt und nicht innerhalb von zwei Wochen
abschließbar ist, wird die laufende Migrationsumsetzung für diese Phase eingefroren,
es erfolgt ein Replan-PR mit dokumentierter Ursache und eine ADR-100-Neubewertung,
bevor weitere Slice-Phasen gestartet werden.

## Validierung

Die Entscheidung gilt als **bestätigt** nach Abschluss von Phase 1 (`drift-config`), wenn:

1. `uv sync` im Workspace-Root ohne Fehler läuft.
2. `pytest tests/test_config.py tests/test_config_schema.py -q` grün.
3. `drift --version` aus dem installierten Meta-Paket korrekt auflöst.
4. `drift analyze --repo . --exit-zero` produziert identisches Finding-Set wie vor Phase 1.
5. `make check` vollständig grün.

### Phasen-spezifische Zusatz-Gates

Zusätzlich zu den fünf Basis-Kriterien gelten je Phase folgende Zusatzprüfungen:

| Phase | Zusatz-Gate |
|-------|-------------|
| 2 (`drift-sdk`) | API- und Modell-Imports in bestehenden `from drift.X`-Callsites bleiben ohne Testanpassung auflösbar |
| 3 (`drift-engine`) | Analyzer-Pipeline-Regressionstest gegen repräsentatives Fixture-Set (inkl. Signale + Scoring) grün |
| 4a (`drift-output`) | CLI- und JSON/SARIF-Output-Snapshots bleiben format- und schema-kompatibel |
| 4b (`drift-session`) | dedizierte Session-Integrationssuite (u.a. Session-Loop/Handover/Task-Graph) grün |
| 5a (`drift-mcp`) | MCP-Router- und Tool-Contract-Tests grün, keine Routing-Regression in Session-gebundenen Tools |
| 5b (`drift-cli`) | End-to-end CLI-Command-Dispatch inkl. Entry-Points weiterhin funktional |
| 6a | Re-export-Stubs vollständig, `drift --version` und Kernimporte aus Consumer-Sicht unverändert |
| 6b | Workflow-Path-Filter decken `packages/**` vollständig ab, ohne unbeabsichtigte Trigger-Lücken |
| 6c | Guard-Skills/Docs konsistent mit Paketpfaden, keine Referenzen auf veraltete `src/drift/**`-Pfade |

Referenz Policy §10 Lernzyklus: offen bis Phase-1-Validierung.
