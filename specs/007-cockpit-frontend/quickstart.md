# Quickstart: Drift Cockpit Frontend

**Date**: 2026-05-02

## Prerequisites

- Node.js 20+
- Python 3.11+ with drift dev install (`pip install -e '.[dev]'`)
- The `drift-cockpit` backend package installed (part of workspace)

---

## Local Development (full stack)

### 1. Start the backend API

```bash
drift cockpit build --repo . --pr 123
drift cockpit serve --port 8001
```

This starts the cockpit API at `http://localhost:8001`.

### 2. Start the frontend dev server

```bash
cd packages/cockpit-ui
npm install
COCKPIT_API_URL=http://localhost:8001 npm run dev
```

Open `http://localhost:3000/cockpit/mick-gsk/drift/123`.

---

## Building static assets for Python bundling

```bash
cd packages/cockpit-ui
COCKPIT_API_URL=__COCKPIT_API_URL__ npm run build   # placeholder replaced at serve time
# Output: packages/cockpit-ui/out/
```

Copy output to Python package:
```bash
cp -r packages/cockpit-ui/out/* packages/drift-cockpit/src/drift_cockpit/static/
```

The Python wheel (built by hatchling) embeds `static/` as package data.

---

## Running with `drift cockpit serve` (production-like)

```bash
drift cockpit serve --port 8000 --api-url http://localhost:8001
```

Open `http://localhost:8000/cockpit/mick-gsk/drift/123`.

The command:
1. Locates `static/` via `importlib.resources`
2. Serves HTML/JS/CSS from the embedded Next.js export
3. Proxies `/api/cockpit/*` to `--api-url`

---

## Key URLs

| URL | Content |
|-----|---------|
| `http://localhost:3000/cockpit/{owner}/{repo}/{pr}` | Decision Panel (main view) |
| `http://localhost:3000/cockpit/{owner}/{repo}/{pr}?tab=ledger` | Decision Ledger tab |
| `http://localhost:3000/cockpit/{owner}/{repo}/{pr}?tab=graph` | Accountability Graph tab |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COCKPIT_API_URL` | `http://localhost:8001` | Backend API base URL |
| `COCKPIT_PORT` | `3000` (dev) / `8000` (serve) | Frontend server port |

---

## Running tests

```bash
# Frontend (component + E2E)
cd packages/cockpit-ui
npm test                    # Vitest unit + integration
npm run test:e2e            # Playwright E2E

# Python serve command
cd c:\Users\mickg\PWBS\drift
.venv\Scripts\python.exe -m pytest tests/decision_cockpit/ -q --tb=short
```
