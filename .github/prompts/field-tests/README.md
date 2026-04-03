# Drift Field-Test-Prompts

> Externe Validierung: Drift in beliebigen Repositories testen.

## Zweck

Diese Prompts testen den Drift-Analyzer in **beliebigen Repositories** — nicht nur im Drift-Repo selbst. Externe Repos sind der Härtetest für Signal-Precision, False-Positive-Rate und Output-Nützlichkeit.

**Issues gehen immer an `mick-gsk/drift`** — nicht ans analysierte Ziel-Repo.

## Voraussetzungen

- Python ≥ 3.11
- Git installiert
- `pip install drift-analyzer` (oder `uv pip install drift-analyzer`)
- Ein Repository mit mindestens einem Git-Commit

## Prompts

| Prompt | Zweck | Voraussetzung |
|--------|-------|---------------|
| [drift-field-test](drift-field-test.prompt.md) | Smoke-Test: Funktioniert drift in diesem Repo? | Keine |
| [drift-finding-audit](drift-finding-audit.prompt.md) | Tiefenprüfung: Sind die Findings korrekt? TP/FP/FN messen | field-test = `pass` |
| [drift-context-eval](drift-context-eval.prompt.md) | Kontext-Qualität: Sind Exports nützlich für AI-Workflows? | field-test = `pass` |

## Empfohlene Reihenfolge

```
1. drift-field-test     → Kann drift dieses Repo analysieren?
2. drift-finding-audit  → Sind die Findings korrekt?
3. drift-context-eval   → Sind die Exports nützlich?
```

Jeder Prompt kann einzeln ausgeführt werden, aber `finding-audit` und `context-eval` setzen voraus, dass `field-test` bestanden hat.

## Shared Components

Die Field-Test-Prompts nutzen dieselben Partials wie die internen Prompts:

| Datei | Inhalt |
|-------|--------|
| `../_partials/bewertungs-taxonomie.md` | Einheitliche Bewertungs-Labels |
| `../_partials/konventionen.md` | Policy-Gate, Datumsformat, Artefakt-Pfade |
| `../_partials/issue-filing-external.md` | Issue-Template für Cross-Repo-Tests |

## Artefakte

Alle Artefakte werden im Ziel-Repo unter `work_artifacts/` erstellt:

```
work_artifacts/field_test_<YYYY-MM-DD>/
work_artifacts/finding_audit_<YYYY-MM-DD>/
work_artifacts/context_eval_<YYYY-MM-DD>/
```

## Unterschied zu den internen Prompts

| Aspekt | Interne Prompts | Field-Test-Prompts |
|--------|----------------|-------------------|
| Ziel-Repo | Drift selbst | Beliebiges Repo |
| Drift-Wissen | Kann Interna nutzen | Nur CLI-Signale |
| Oracle | `ground_truth_labels.json` | Aus Repo-Architektur abgeleitet |
| Issues an | `mick-gsk/drift` | `mick-gsk/drift` |
| Issue-Template | `issue-filing.md` | `issue-filing-external.md` |
