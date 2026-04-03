# CI Soft-Rollout — Vorschlag

**Rollout Analyst Report**  
**Datum:** 2026-03-30  
**Basiert auf:** Validierung von 3 Repos (marshmallow, scrapy, paramiko)

---

## 1. Empfohlene Einführung ohne Hard-Gating

### Phase A: Visibility Only (Woche 1–4)

```yaml
# .github/workflows/drift.yml
name: Drift Analysis
on:
  pull_request:
    paths: ['**/*.py']
  push:
    branches: [main, master]

jobs:
  drift:
    runs-on: ubuntu-latest
    continue-on-error: true  # KEIN Gate
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 100
      - uses: mick-gsk/drift@v1
        with:
          args: >-
            check
            --fail-on critical
            --compact
            --json
            --output drift-report.json
      - uses: actions/upload-artifact@v4
        with:
          name: drift-report
          path: drift-report.json
```

**Kernprinzipien:**
- `continue-on-error: true` — Workflow blockiert nie einen Merge
- `--compact` — Reduziert Token-Last und Noise
- `--fail-on critical` — Nur Critical-Findings loggen (nicht high/medium)
- Output als Artefakt verfügbar, aber nicht im PR-Kommentar

### Phase B: PR-Kommentar (Woche 5–8)

Erweiterung um automatischen PR-Kommentar mit fix_first-Liste:

```yaml
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('drift-report.json', 'utf8'));
            const fixFirst = report.fix_first || [];
            if (fixFirst.length === 0) return;
            
            let body = '## 🔍 Drift Analysis\n\n';
            body += `Score: **${report.drift_score}** | Severity: **${report.severity}**\n\n`;
            body += '### Top Findings\n\n';
            fixFirst.slice(0, 5).forEach((f, i) => {
              body += `${i+1}. **[${f.severity}]** ${f.title}\n`;
              body += `   ${f.file}:${f.start_line || ''} — ${f.next_step?.slice(0, 100) || 'N/A'}\n\n`;
            });
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body
            });
```

### Phase C: Soft Gate (Woche 9–12)

```yaml
      - name: Drift Gate
        if: github.event_name == 'pull_request'
        run: |
          SCORE=$(python -c "import json; print(json.load(open('drift-report.json'))['drift_score'])")
          if (( $(echo "$SCORE > 0.7" | bc -l) )); then
            echo "::warning::Drift score $SCORE exceeds soft threshold 0.7"
          fi
```

- Warning statt Failure bei Score > 0.7
- Reviewer sieht die Warnung, kann aber mergen

---

## 2. Trigger

| Trigger | Empfehlung | Begründung |
|---------|-----------|------------|
| PR auf main/master | ✅ Immer | Hauptanwendungsfall |
| Push auf main/master | ✅ Immer | Baseline-Tracking |
| Schedule (weekly) | ⚠️ Optional | Trend-Monitoring, aber nicht initial |
| PR auf Feature-Branches | ❌ Nicht empfohlen | Zu hohe CI-Last, geringe Relevanz |

---

## 3. Schwellwerte

| Schwellwert | Phase A/B | Phase C | Hard Gate |
|-------------|-----------|---------|-----------|
| `--fail-on` | critical | critical | high |
| Score-Warning | — | > 0.7 | > 0.5 |
| Max Findings | — | — | < 50 (new findings) |

**Begründung:** Basierend auf den Validierungen:
- marshmallow (sauberes Repo): Score 0.334, 63 Findings → kein Gate nötig
- paramiko (gewachsen): Score 0.477, 275 Findings → Soft-Warning ab 0.5
- scrapy (komplex): Score 0.586, 714 Findings → Hard Gate erst bei stabilem FP-Filter

---

## 4. Sichtbarkeit der Ergebnisse

| Kanal | Phase A | Phase B | Phase C |
|-------|---------|---------|---------|
| CI-Artefakt (JSON) | ✅ | ✅ | ✅ |
| PR-Kommentar | ❌ | ✅ (Top 5) | ✅ (Top 5 + Warning) |
| SARIF Upload | ❌ | ❌ | ✅ (GitHub Code Scanning) |
| Dashboard/Badge | ❌ | ❌ | Optional |

---

## 5. Wann ein Hard-Gate sinnvoll wäre

Ein Hard-Gate (`continue-on-error: false`) ist erst empfehlenswert, wenn:

1. **FP-Rate unter 15%** — aktuell ~23% (7/30), zu hoch für Blocking
2. **AVS-Duplikate bereinigt** — doppelte Findings erzeugen Frustration
3. **DCA-Library-Mode existiert** — ohne diesen blocken Libraries unnötig
4. **Team hat 4+ Wochen Erfahrung** — Soft-Rollout muss akzeptiert sein
5. **Baseline existiert** — Nur neue Findings sollen blocken, nicht Bestand

**Frühester Zeitpunkt für Hard-Gate:** 12–16 Wochen nach Soft-Rollout-Start.

---

## 6. Risiken bei zu früher Durchsetzung

| Risiko | Wahrscheinlichkeit | Impact |
|--------|-------------------|--------|
| FP blockiert legitime PRs → Frustration | Hoch | Hoch |
| Team beginnt drift-Findings pauschal zu ignorieren | Mittel | Hoch |
| DCA-FPs bei Libraries führen zu Workarounds | Hoch | Mittel |
| AVS-Duplikate suggerieren mehr Probleme als vorhanden | Mittel | Mittel |
| PFS-Volumen überfordert bei großen Repos | Mittel | Niedrig |

**Fazit:** Soft-Rollout mit `continue-on-error: true` ist zwingend notwendig, bevor ein Gate aktiviert wird.
