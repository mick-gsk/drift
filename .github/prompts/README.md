# Drift Prompt-Bibliothek

> Übersicht aller Evaluierungs- und Workflow-Prompts im Drift-Workspace.

## Schnellübersicht

| Prompt | Zweck | Relevanter Skill | Relevante Instruction | Wann verwenden |
|--------|-------|-------------------|----------------------|----------------|
| [drift-harness-engine](drift-harness-engine.prompt.md) | Harness-Engine-Audit: Maps, Contracts, Feedback-Loops, Agentenlesbarkeit und Entropieabwehr im Workspace verbessern | `drift-agent-prompt-authoring` | `drift-policy`, `drift-prompt-engineering` | Wenn Agenten die Workspace-Harness-Engine statt Produktoberflaechen verbessern sollen |
| [drift-context-engineering](drift-context-engineering.prompt.md) | Context-Engineering-Audit: statischer Kontext, dynamischer Kontext, Freshness, Single Source of Truth und repo-lokale Kontextluecken bewerten | `drift-agent-prompt-authoring` | `drift-policy`, `drift-prompt-engineering` | Wenn unklar ist, ob Agenten im Workspace ueber die richtigen und ausreichend frischen Informationen verfuegen |
| [drift-harness-followup](drift-harness-followup.prompt.md) | Harness-Follow-up: bestehenden Artefaktordner lesen, naechsten offenen Hebeldefekt waehlen und eng umsetzen | `drift-agent-prompt-authoring` | `drift-policy`, `drift-prompt-engineering` | Nach einem Lauf von `drift-harness-engine`, wenn aus den Artefakten die naechste gezielte Verbesserung abgeleitet werden soll |
| [drift-context-engineering-followup](drift-context-engineering-followup.prompt.md) | Context-Engineering-Follow-up: offenen Kontext-Gap aus Context-Engineering-Artefakten lesen und genau eine Repo-Aenderung umsetzen | `drift-agent-prompt-authoring` | `drift-policy`, `drift-prompt-engineering` | Nach einem Lauf von `drift-context-engineering`, wenn der naechste offene Kontext-Hebel direkt umgesetzt werden soll |
| [drift-agent-ux](drift-agent-ux.prompt.md) | Agent-UX-Audit: Entscheidungsketten, Dead Ends, Recovery-Pfade | — | `drift-policy` | Agent-Nutzbarkeit der CLI bewerten |
| [drift-agent-workflow-test](drift-agent-workflow-test.prompt.md) | Vollständiger CLI-Coverage-Test über alle Kommandos | — | `drift-policy` | Komplette CLI-Oberfläche testen |
| [drift-ai-integration](drift-ai-integration.prompt.md) | LLM-Kontext-Qualität: Export-Formate, MCP, Token-Effizienz | — | `drift-policy` | AI-Integrations-Tauglichkeit prüfen |
| [drift-ci-gate](drift-ci-gate.prompt.md) | CI-Sicherheit: Exit-Codes, Idempotenz, Maschinen-Formate | — | `drift-policy`, `drift-push-gates` | CI-Pipeline-Tauglichkeit validieren |
| [drift-fp-reduction](drift-fp-reduction.prompt.md) | FP-Reduktionsaudit: Thresholds, Negative Context, Guardrails, Suppression, Kalibrierung, Scoring | — | `drift-policy` | False Positives systematisch priorisieren und absichern |
| [drift-onboarding](drift-onboarding.prompt.md) | Erstnutzer-Friktionstest: Init, Config, Time-to-Value | — | `drift-policy` | Onboarding-Qualität für neue User bewerten |
| [drift-signal-quality](drift-signal-quality.prompt.md) | Signalkorrektheit: TP/FP/FN, Precision/Recall, Oracle-Abgleich | — | `drift-policy` | Signalqualität und -vertrauen messen |
| [PR-Orchestrator](PR-Orchestrator.prompt.md) | Risikobasierte PR-Review-Entscheidung (APPROVE/MERGE/WAIT/...) | `drift-pr-review` | `drift-policy` | Pull Requests bewerten und entscheiden |
| [release](release.prompt.md) | Release-Workflow: Version, Changelog, Tag, Publish | `drift-release` | `drift-release-automation`, `drift-release-mandatory` | Nach Code-Änderungen releasen |

## Empfohlene Reihenfolge für vollständige Produkt-Evaluation

Für eine umfassende Drift-Bewertung diese Prompts in dieser Reihenfolge ausführen:

1. **drift-onboarding** — Ersteinrichtung und Time-to-Value
2. **drift-agent-workflow-test** — Vollständige CLI-Abdeckung in realistischen Workflows
3. **drift-signal-quality** — Signalkorrektheit und -vertrauen messen
4. **drift-ci-gate** — CI-Pipeline-Sicherheit und -Stabilität
5. **drift-ai-integration** — LLM-Kontext-Qualität und MCP-Tauglichkeit
6. **drift-agent-ux** — Autonomes Agent-UX-Audit (baut auf Ergebnissen der vorherigen auf)

## Harness-Engine statt Produkt-Evaluation

Wenn die Aufgabe nicht die Drift-CLI oder das Produktverhalten selbst, sondern die agentische Arbeitsumgebung des Workspaces verbessern soll, zuerst **drift-harness-engine** verwenden.

Der Prompt ist bewusst intern ausgerichtet und startet an Repo-Maps, Contracts und Harness-Checks statt an `drift-analyzer`-Produktflaechen. Das vermeidet, dass Agenten versehentlich in CLI- oder Field-Test-Prompts kippen, obwohl eigentlich die Workspace-Harness-Engine das Ziel ist.

Wenn der groesste Engpass nicht die gesamte Harness-Engine, sondern speziell der verfuegbare Agenten-Kontext ist, zuerst **drift-context-engineering** verwenden. Dieser Prompt trennt bewusst zwischen statischem Kontext, dynamischem Kontext, Freshness und Single-Source-of-Truth-Luecken.

Wenn bereits ein Artefaktordner aus einem Harness-Lauf existiert und **kein neues Voll-Audit**, sondern der naechste gezielte Folgeschritt gewuenscht ist, danach **drift-harness-followup** verwenden. Dieser Prompt baut bewusst auf `harness_engine_report.md`, `leverage_findings.md` und `autonomy_ladder.md` auf, statt die gesamte Harness-Analyse erneut breit aufzurollen.

## Tägliche Workflows

| Situation | Prompt |
|-----------|--------|
| PR bewerten und Merge-Entscheidung treffen | **PR-Orchestrator** |
| Neue Version veröffentlichen | **release** |

## Relevanter Skill für Prompt-Authoring

Für neue oder überarbeitete Prompt-Dateien verwende den Skill `drift-agent-prompt-authoring` unter `.github/skills/drift-agent-prompt-authoring/SKILL.md`.

## Field-Test-Prompts (externe Repos)

Prompts unter `field-tests/` testen drift in **beliebigen Repositories** — nicht nur im Drift-Repo.
Details: [field-tests/README.md](field-tests/README.md)

| Prompt | Zweck | Voraussetzung |
|--------|-------|---------------|
| [drift-field-test](field-tests/drift-field-test.prompt.md) | Smoke-Test: Funktioniert drift in diesem Repo? | Keine |
| [drift-finding-audit](field-tests/drift-finding-audit.prompt.md) | Tiefenprüfung: Findings korrekt? TP/FP/FN | field-test = `pass` |
| [drift-context-eval](field-tests/drift-context-eval.prompt.md) | Kontext-Qualität: Exports nützlich für AI? | field-test = `pass` |

**Issues gehen an `mick-gsk/drift`**, nicht ans analysierte Ziel-Repo.

## Shared Components

Alle Prompts nutzen gemeinsame Referenz-Dateien unter `_partials/`:

| Datei | Inhalt |
|-------|--------|
| [`_partials/bewertungs-taxonomie.md`](_partials/bewertungs-taxonomie.md) | Einheitliches Bewertungssystem (Labels, Scores, Klassifikationen) |
| [`_partials/context-engineering-contract.md`](_partials/context-engineering-contract.md) | Shared Contract fuer statischen Kontext, dynamischen Kontext, Freshness und Single-Source-of-Truth-Pruefung |
| [`_partials/konventionen.md`](_partials/konventionen.md) | Policy-Gate-Pflicht, Datumsformat, Artefakt-Pfade, Sandbox-Erstellung |
| [`_partials/issue-filing.md`](_partials/issue-filing.md) | Issue-Template für interne Prompts |
| [`_partials/issue-filing-external.md`](_partials/issue-filing-external.md) | Issue-Template für Field-Test-Prompts (Cross-Repo) |

## Beziehung zum Instructions/Skills-Ökosystem

```
.github/copilot-instructions.md          ← Master-Arbeitsvertrag für alle Agenten
  ├── .github/instructions/
  │   ├── drift-policy.instructions.md    ← Policy-Gate, Qualitätsanforderungen, Prioritäten
  │   ├── drift-push-gates.instructions.md ← Pre-Push-Validierung (8 Gates)
  │   ├── drift-release-automation.instructions.md ← PSR-Workflow (DE)
  │   └── drift-release-mandatory.instructions.md  ← PSR-Pflicht (EN)
  ├── .github/skills/
  │   ├── drift-agent-prompt-authoring/SKILL.md ← Prompt-Authoring für `.github/prompts/`
  │   ├── drift-pr-review/SKILL.md        ← PR-Review-Checklist → verwendet von PR-Orchestrator
  │   ├── drift-release/SKILL.md          ← Release-Workflow → verwendet von release.prompt.md
  │   └── drift-security-triage/SKILL.md  ← Security-Triage (kein Prompt)
  └── .github/prompts/                    ← Diese Prompt-Bibliothek
```

## Konventionen

- **Sprache**: Alle Prompts sind auf Deutsch
- **Bewertungssystem**: Einheitlich gemäß `_partials/bewertungs-taxonomie.md`
- **Issue-Erstellung**: Einheitlich gemäß `_partials/issue-filing.md`
- **Modellbezug**: Prompts sind modellunabhängig (keine spezifische Modellversion)
- **Artefakte**: Unter `work_artifacts/<prompt-kürzel>_<YYYY-MM-DD>/`
