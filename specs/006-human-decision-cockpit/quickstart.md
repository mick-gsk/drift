# Quickstart: Human Decision Cockpit

## Ziel

In weniger als 10 Minuten lokal einen PR-Entscheidungsdurchlauf erzeugen: Decision Panel, Minimal Safe Plan, Accountability Cluster und Ledger-Eintrag.

## Voraussetzungen

- Workspace installiert mit Dev-Dependencies (`pip install -e '.[dev]'`)
- Frontend-Toolchain verfuegbar im `playground/` (Node + npm)
- Ein PR-Diff oder Testfixture vorhanden

## 1. Cockpit-Artefakte bauen

```bash
# Beispielkommando (geplante CLI fuer dieses Feature)
drift cockpit build \
  --repo . \
  --pr-id 1234 \
  --diff-file work_artifacts/pr_1234.diff \
  --out-dir .drift/cockpit
```

Erwartete Artefakte:
- `.drift/cockpit/pr-1234/decision.json`
- `.drift/cockpit/pr-1234/safe_plan.json`
- `.drift/cockpit/pr-1234/clusters.json`
- `.drift/cockpit/ledger.jsonl`

## 2. Web-App lokal starten

```bash
cd playground
npm install
npm run dev
```

Dann im Browser den Cockpit-Bereich fuer `pr_id=1234` oeffnen.

## 3. Menschliche Entscheidung dokumentieren

Im Cockpit:
- Empfehlung pruefen
- Falls Uebersteuerung: Pflicht-Begruendung eintragen
- Entscheidung speichern

Alternativ per API (geplante Route):

```bash
curl -X POST http://localhost:4173/api/cockpit/prs/1234/decision \
  -H "Content-Type: application/json" \
  -d '{
    "human_status": "go_with_guardrails",
    "override_reason": "critical fix validated in patch set 2",
    "decision_actor": "maintainer@example.com",
    "version": 4
  }'
```

## 4. 7/30-Tage Outcome erfassen

```bash
# Beispielkommando (geplante CLI)
drift cockpit outcome update \
  --repo . \
  --pr-id 1234 \
  --window 7d \
  --state captured \
  --rework-events 0 \
  --merge-velocity-delta 0.03
```

## 5. Akzeptanz-Schnellcheck

- Genau ein Decision Status sichtbar.
- No-Go zeigt mindestens einen konkreten Minimal-Safe-Plan.
- Ledger enthaelt Empfehlung, Human-Entscheidung, Evidenz und Outcome-Status.
- Fehlende Outcomes werden als `pending` angezeigt.
- Parallel-Update mit alter Version erzeugt sichtbaren Konflikt.
