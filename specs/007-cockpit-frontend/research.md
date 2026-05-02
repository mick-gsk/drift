# Research: Drift Cockpit Frontend

**Phase**: 0 — Unknowns resolved before design  
**Date**: 2026-05-02  
**For**: [plan.md](plan.md)

---

## Decision 1: PR-Identifikation via URL-Routing

**Decision**: Path-Segment-Routing — `/cockpit/[owner]/[repo]/[pr_number]`

**Rationale**: `next export` rendert jede Route als eigene HTML-Datei. Path-Segmente (`[owner]/[repo]/[pr_number]`) sind für Static-Export der zuverlässigste Ansatz, weil jedes eindeutige PR ein eigenes pre-gerendertes HTML-Dokument erhält. Query-Parameter (z. B. `?pr=https://github.com/...`) würden rein client-seitig verarbeitet und machen URLs fragilere Bookmarks. Zusätzliche UI-Zustände (aktiver Tab: Ledger, Graph) nutzen Query-Params innerhalb der Seite (`?tab=ledger`).

**Alternatives considered**: Query-Parameter-basiertes Routing — verworfen, da kein pre-rendered HTML pro PR möglich und keine verlässlichen direkten Links ohne JS.

---

## Decision 2: Next.js Static Export + Python Bundling

**Decision**: Next.js `output: 'export'` → `out/` wird nach `src/drift_cockpit/static/` kopiert; Hatchling-Include-Glob bundelt die Assets in das Python-Wheel.

**Rationale**: `output: 'export'` erzeugt voll-statisches HTML/JS/CSS aus Next.js. Diese Dateien landen in `packages/drift-cockpit/src/drift_cockpit/static/` und werden über Hatchling als Package-Data eingebettet. Zur Laufzeit lokalisiert `importlib.resources` das `static/`-Verzeichnis im installierten Paket. Für den HTTP-Server wird FastAPI + uvicorn gewählt, da es im gleichen Prozess sowohl statische Assets als auch die REST-API-Endpunkte bedienen kann — und uvicorn wahrscheinlich ohnehin als transitive Abhängigkeit vorliegt.

**Alternatives considered**: Python `http.server.SimpleHTTPRequestHandler` — verworfen, da POST/PATCH für Ledger-Updates einen separaten Handler-Mechanismus erfordern würden, der FastAPI nicht vereinfacht.

---

## Decision 3: In-Progress-Scan-Zustand — Polling statt SSE/WebSocket

**Decision**: Client-seitiges Polling via `setInterval` + `fetch` auf `GET /api/cockpit/scan-status/{pr_id}`

**Rationale**: Next.js Static Export läuft rein client-seitig im Browser. SSE und WebSocket erfordern eine persistente Server-Verbindung und werden im Static-Export-Modus nicht vom Next.js-Framework bereitgestellt. Polling ist das praktische Muster: Das Frontend fragt alle 3 Sekunden den Backend-Endpunkt ab, der `{"status": "running"|"complete", "progress": 0..100}` zurückgibt. Für den Governance-Workflow (keine Hochfrequenz-Updates) ist Polling vollständig ausreichend.

**Alternatives considered**: SSE — verworfen, da Static Export keine Server-Push-Infrastruktur bereitstellt. WebSocket — verworfen aus demselben Grund und wegen erhöhter Komplexität ohne nennenswerten Nutzen.

---

## Decision 4: `drift cockpit serve` Erweiterung

**Decision**: Neues `serve`-Subcommand in `_cmd.py` via `@cockpit_cmd.command('serve')` mit `importlib.resources` für Asset-Lokalisierung + FastAPI-App für kombiniertes Serving.

**Rationale**: `importlib.resources.files("drift_cockpit").joinpath("static")` lokalisiert die gebündelten Assets zur Laufzeit. Das Subcommand akzeptiert `--port` (default 8000) und `--api-url` (default `http://localhost:8001`). FastAPI mountet die statischen Assets über `StaticFiles` und stellt gleichzeitig die REST-Endpunkte bereit. So läuft das Frontend ohne separaten Prozess oder Node.js-Runtime.

**Alternatives considered**: Eigenständige Next.js-Runtime — verworfen (erfordert Node.js auf Maintainer-Maschinen). Eigenständiger Python-`http.server` — verworfen wegen fehlender POST/PATCH-Unterstützung ohne Boilerplate.
