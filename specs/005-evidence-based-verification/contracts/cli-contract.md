# CLI Contract: drift verify

**Feature 005 — Evidence-Based Drift Verification**

---

## Command: `drift verify`

```
drift verify [OPTIONS]
```

Prüft ein Change-Set gegen Architekturregeln, Spec-Akzeptanzkriterien und optionalen Independent Review. Gibt ein Evidence Package als JSON oder Rich-Ausgabe zurück.

---

## Options

| Flag | Typ | Default | Beschreibung |
|---|---|---|---|
| `--diff PATH` | Path | — | Unified-Diff-Datei (stdin wenn `-`) |
| `--repo PATH` | Path | `.` | Wurzel des zu analysierenden Repos |
| `--spec PATH` | Path | `None` | Pfad zu `spec.md` für Confidence-Check |
| `--format [json\|rich\|sarif]` | Choice | `rich` | Ausgabeformat (sarif für CI/GitHub Actions) |
| `--reviewer / --no-reviewer` | Flag | `--reviewer` | Independent Reviewer Agent aktivieren |
| `--reviewer-timeout INTEGER` | int | `60` | Timeout in Sekunden für den Reviewer-Agent |
| `--threshold-drift FLOAT` | float | `0.3` | Drift Score Schwellwert für `automerge` (≤ = ok) |
| `--threshold-confidence FLOAT` | float | `0.8` | Spec Confidence Schwellwert für `automerge` (≥ = ok) |
| `--promote-threshold INTEGER` | int | `5` | Anzahl Vorkommen für Rule-Promotion-Vorschlag |
| `--output PATH` | Path | `None` | JSON in Datei schreiben |
| `--exit-zero` | Flag | off | Immer Exit 0 (auch bei `needs-fix`) |

---

## Exit Codes

| Code | Bedeutung |
|---|---|
| 0 | `automerge` oder `--exit-zero` gesetzt |
| 1 | `needs_fix` — mindestens ein Blocker |
| 2 | `needs_review` — kein eindeutiges Urteil |
| 3 | `escalate_to_human` |
| 10 | Eingabefehler (kein Diff, ungültiger Pfad) |

---

## JSON Output: Evidence Package Schema (v1)

```json
{
  "schema": "evidence-package-v1",
  "version": "<drift-version>",
  "change_set_id": "<sha256-of-diff>",
  "repo": "<repo-path>",
  "verified_at": "<ISO-8601>",
  "drift_score": 0.0,
  "spec_confidence_score": 1.0,
  "action_recommendation": {
    "verdict": "automerge | needs_fix | needs_review | escalate_to_human",
    "reason": "<one sentence>",
    "blocking_violation_count": 0
  },
  "violations": [
    {
      "violation_type": "layer_violation | forbidden_dependency | file_placement | naming_convention | rule_conflict",
      "severity": "critical | high | medium | low",
      "file": "<relative-path>",
      "line": 42,
      "rule_id": "AVS",
      "conflicting_rule_id": null,
      "message": "<what was found>",
      "remediation": "<what to do>"
    }
  ],
  "functional_evidence": {
    "tests_passed": true,
    "tests_total": 120,
    "tests_failing": 0,
    "lint_passed": true,
    "typecheck_passed": true,
    "screenshots": [],
    "logs": [],
    "metrics": {}
  },
  "independent_review": {
    "available": true,
    "confidence_delta": 0.05,
    "findings": [],
    "spec_criteria_violated": []
  },
  "rule_promotions": [
    {
      "pattern_key": "layer_violation::src/drift/commands/",
      "occurrence_count": 5,
      "threshold": 5,
      "suggested_rule_id": "CUSTOM-001",
      "suggested_description": "...",
      "affected_files": []
    }
  ],
  "flags": []
}
```

**Schema-Validierung**: `scripts/generate_evidence_schema.py` (analog zu `generate_output_schema.py`) — CI-Gate über `tests/test_evidence_schema.py`.

---

## Invarianten

- `violations` ist leer wenn `flags` enthält `no_changes_detected`
- `action_recommendation.verdict == "automerge"` **nur wenn** `violations == []` AND `drift_score ≤ threshold_drift` AND `spec_confidence_score ≥ threshold_confidence` — alle drei Bedingungen müssen erfüllt sein; `drift_score == 0.0` allein reicht nicht
- `independent_review` ist `null` wenn `--no-reviewer` gesetzt oder `independent_review.available == false` (Timeout)
- Bei `flags` enthält `rule_conflict`: `action_recommendation.verdict` ist mindestens `needs_review`
- `flags` enthält `no_changes_detected` → `action_recommendation.verdict == "automerge"` (Kurzpfad, kein Score-Check nötig)
