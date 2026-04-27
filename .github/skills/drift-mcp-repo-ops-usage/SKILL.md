---
name: drift-mcp-repo-ops-usage
description: "Operationaler Workflow für den internen MCP-Server aus scripts/mcp_product_health_server.py. Immer verwenden, wenn Agenten Produktstatus, Release-Gates, Working-Tree-Gates oder Audit-Freshness direkt per MCP abrufen sollen statt manuelle Git-/Script-Aufrufe zu bauen. Keywords: drift_product_health, drift_release_readiness, drift_working_tree_context, drift_audit_freshness, mcp server, pre-push gates, blast report, audit freshness."
argument-hint: "Beschreibe, welche Entscheidung du treffen willst (Health-Check, Release-Go/No-Go, Push-Vorbereitung, Audit-Freshness)."
---

# Drift MCP Repo Ops Usage

Nutze diesen Skill, um den internen MCP-Server in [scripts/mcp_product_health_server.py](scripts/mcp_product_health_server.py) konsistent zu verwenden.

Ziel: Agenten sollen wiederkehrende Repo-Operations direkt per MCP-Tool auslesen, statt dieselben Prüfungen manuell per Terminal zu rekonstruieren.

## Wann verwenden

- User fragt nach Produktgesundheit oder Adoption/Performance/Stability-Status.
- User will eine schnelle Release-Entscheidung (GO/NO_GO) vor Push.
- User will wissen, welche Pre-Push-Gates durch den aktuellen Working Tree ausgelöst werden.
- User will prüfen, ob §18-Audit-Artefakte gegenüber Signal-Änderungen veraltet sind.

## Wann nicht verwenden

- Für normale Drift-Codeanalyse im Ziel-Repo: dafür die Drift-MCP-Tools (`drift_scan`, `drift_diff`, `drift_nudge`, ...) verwenden.
- Für Azure-, Foundry- oder Cloud-Operations.
- Wenn der interne Server nicht registriert ist und der User explizit nur CLI-Workflow möchte.

## Vorbedingungen

1. MCP-Dependency ist installiert:

```bash
.venv\Scripts\python.exe -m pip install -e ".[mcp]"
```

2. Der Server ist in [\.vscode/mcp.json](.vscode/mcp.json) registriert und zeigt auf:

- command: `.venv/Scripts/python.exe` (oder passender Python-Pfad)
- args: `scripts/mcp_product_health_server.py`

3. Bei fehlender Tool-Verfügbarkeit zuerst MCP-Server-Konfiguration reparieren, dann erneut aufrufen.

## Tool-Übersicht

1. `drift_product_health(refresh=False)`
- Liefert Adoption, Stability, Performance aus KPI-Snapshot.
- `refresh=True` nur nutzen, wenn Live-APIs wirklich nötig sind.

2. `drift_release_readiness()`
- Liefert `status: GO|NO_GO`, `blockers`, `warnings`, `agent_instruction`.
- Prüft u. a. Version-Sync (`pyproject.toml`, `CHANGELOG.md`, `SECURITY.md`, `llms.txt`) und Blast-Report-Erwartung.

3. `drift_working_tree_context()`
- Liefert geänderte Bereiche, inferred commit type, getriggerte Gates, empfohlene nächste Aktion.

4. `drift_audit_freshness()`
- Liefert Freshness der Audit-Artefakte relativ zum letzten `src/drift/signals/`-Commit.

## Standard-Workflow

### 1. Zielentscheidung klären

Ordne die Anfrage einer Entscheidung zu:

- Produktstatus: `drift_product_health`
- Release-Go/No-Go: `drift_release_readiness`
- Push-Vorbereitung/Gate-Prognose: `drift_working_tree_context`
- Audit-Pflicht/Freshness: `drift_audit_freshness`

### 2. Minimal notwendige Tool-Reihenfolge wählen

- Release vor Push: `drift_working_tree_context` -> `drift_release_readiness`
- Signal-nahe Änderung: `drift_working_tree_context` -> `drift_audit_freshness`
- Weekly Health: `drift_product_health(refresh=False)`

Erst weitere Tools aufrufen, wenn die erste Antwort eine Unklarheit offen lässt.

### 3. Ergebnis in Entscheidungssprache übersetzen

Nutze immer dieses Antwortmuster:

1. Entscheidung in einem Satz (`GO`, `NO_GO`, `Audit fresh`, `Audit stale`, ...)
2. Maximal 3 konkrete Gründe aus den Tool-Feldern
3. Nächste Aktion als einzelner Befehl oder klarer Schritt

## Antwortvorlagen

### Release readiness

- GO-Fall: "Release ist GO. Keine Blocker, Push kann erfolgen."
- NO_GO-Fall: "Release ist NO_GO. Behebe zuerst diese Blocker: ..."

### Working tree context

- "Es sind N Dateien geändert, Commit-Typ wird als X inferiert, diese Gates feuern: ..."
- "Nächster Schritt: make gate-check COMMIT_TYPE=<type>"

### Audit freshness

- Fresh: "Alle §18-Audit-Artefakte sind aktuell."
- Stale: "Diese Artefakte sind veraltet: ..."

### Product health

- "Produktstatus: HEALTHY/WARNING/ALARM mit Fokus auf Delta, Bugs, Budget-Headroom."

## Guardrails

- Keine Aussagen über GO/NO_GO ohne Tool-Output.
- Keine erfundenen Gate-Regeln: nur Felder aus Tool-JSON verwenden.
- `refresh=True` bei `drift_product_health` sparsam einsetzen (externe API-Last).
- Bei `NO_GO` immer blocker-first kommunizieren, nicht mit Nebeninfos beginnen.
- Dieser Skill ist intern für das Drift-Repo, nicht für das veröffentlichte Paket.

## Kurzer Smoke-Check (optional)

Wenn der User den Server selbst testen will:

```bash
.venv\Scripts\python.exe -c "import asyncio, importlib.util; spec=importlib.util.spec_from_file_location('srv','scripts/mcp_product_health_server.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); print(asyncio.run(m.drift_release_readiness()))"
```

## Referenzen

- [scripts/mcp_product_health_server.py](scripts/mcp_product_health_server.py)
- [\.vscode/mcp.json](.vscode/mcp.json)
- [POLICY.md](POLICY.md)
- [.github/instructions/drift-policy.instructions.md](.github/instructions/drift-policy.instructions.md)
- [.github/instructions/drift-push-gates.instructions.md](.github/instructions/drift-push-gates.instructions.md)
