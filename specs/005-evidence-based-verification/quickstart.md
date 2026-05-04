# Quickstart: drift verify

**Feature 005 — Evidence-Based Drift Verification**

---

## Voraussetzungen

- drift installiert (`pip install -e '.[dev]'` im Workspace)
- Git-Repository mit `drift.yaml` (oder defaults)

---

## Minimal-Beispiel: Diff aus Git prüfen

```bash
# Diff des letzten Commits als Datei
git diff HEAD~1 HEAD > my_change.diff

# Evidence Package generieren (Rich-Ausgabe)
drift verify --diff my_change.diff --repo .

# JSON-Output für CI/Agenten
drift verify --diff my_change.diff --repo . --format json

# Mit Spec-Abgleich (Confidence-Score)
drift verify --diff my_change.diff --repo . --spec specs/005-evidence-based-verification/spec.md --format json
```

---

## Evidence Package lesen

```json
{
  "schema": "evidence-package-v1",
  "drift_score": 0.12,
  "spec_confidence_score": 0.91,
  "action_recommendation": {
    "verdict": "automerge",
    "reason": "No violations found; drift and confidence thresholds met.",
    "blocking_violation_count": 0
  },
  "violations": [],
  "flags": []
}
```

**Aktionsempfehlung-Tabelle:**

| verdict | Bedeutung | Exit Code |
|---|---|---|
| `automerge` | Alle Prüfungen bestanden | 0 |
| `needs_fix` | Architekturverletzung oder Test-Fehler | 1 |
| `needs_review` | Unklares Urteil, Review nötig | 2 |
| `escalate_to_human` | Kritischer Befund | 3 |

---

## Layer-Verletzung beheben

Wenn das Evidence Package enthält:

```json
{
  "violations": [{
    "violation_type": "layer_violation",
    "severity": "high",
    "file": "src/drift/commands/analyze.py",
    "line": 42,
    "rule_id": "AVS",
    "message": "Business logic found in CLI command layer",
    "remediation": "Move logic to src/drift/analyze/_checker.py; CLI command should only call library API."
  }]
}
```

→ Logik aus dem CLI-Command in den entsprechenden Bibliotheks-Slice verschieben, dann erneut prüfen.

---

## In CI verwenden

```yaml
# .github/workflows/verify.yml
- name: Evidence-Based Verification
  run: |
    git diff ${{ github.base_ref }}...HEAD > change.diff
    drift verify --diff change.diff --repo . --format json --output evidence.json
  continue-on-error: false

- name: Upload Evidence Package
  uses: actions/upload-artifact@v4
  with:
    name: evidence-package
    path: evidence.json
```

---

## Rule-Promotion annehmen

Wenn das Evidence Package einen `rule_promotions`-Eintrag enthält:

```bash
# Vorgeschlagene Regel permanent aktivieren
drift rules add --id CUSTOM-001 --from-promotion evidence.json
```

(Feature v2 — in v1 manuell via `drift.yaml` rules-Sektion.)

---

## Flags verstehen

| Flag | Bedeutung |
|---|---|
| `no_changes_detected` | Leerer Diff; automerge ohne Prüfung |
| `rule_conflict` | Zwei Regeln widersprechen sich; needs_review |
| `independent_review_unavailable` | Reviewer-Agent war nicht erreichbar |
