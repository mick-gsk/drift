---
name: "drift-context-engineering"
agent: agent
description: "Analysiert die Context-Engineering-Saeule des Workspace-Harnesses: statischer Kontext, dynamischer Kontext, Freshness, Single Source of Truth und repo-lokale Kontextluecken fuer Agenten."
---

# Drift Context Engineering

Du analysierst die erste Saeule des Harness-Engineerings: ob ein Agent zur richtigen Zeit ueber die richtigen Informationen verfuegt und ob diese Informationen repo-lokal sichtbar, hinreichend frisch und fuer Handlungen brauchbar sind.

Der Prompt ist spezialisiert. Er ersetzt kein breites Harness-Audit und keine direkte Folgeumsetzung. Fuer ein allgemeines Hebelaudit verwende `drift-harness-engine.prompt.md`. Fuer die Umsetzung eines bereits identifizierten Kontext-Gaps verwende `drift-context-engineering-followup.prompt.md`.

> **Pflicht:** Vor Ausfuehrung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- `.github/instructions/drift-policy.instructions.md`
- `.github/prompts/_partials/konventionen.md`
- `.github/prompts/_partials/context-engineering-contract.md`
- `.github/copilot-instructions.md`
- `AGENTS.md`
- `DEVELOPER.md`
- `docs/agent-harness-golden-principles.md`
- `scripts/check_agent_harness_contract.py`
- `tests/test_agent_harness_contract.py`
- `drift-harness-engine.prompt.md`
- `drift-context-engineering-followup.prompt.md`
- `drift-harness-followup.prompt.md`

## Ziel

Bestimme, ob der Workspace fuer Agenten ausreichend statischen und dynamischen Kontext bereitstellt, wo die groessten Kontextluecken liegen und welcher naechste Hebeldefekt die Sichtbarkeit, Frische oder Verlaesslichkeit am staerksten verbessert.

## Scope

Pruefe mindestens diese vier Fragen:

1. Welche repo-lokalen statischen Quellen tragen einen Agentenlauf wirklich?
2. Welche dynamischen Signale ueber Zustand, Freshness und Validierung sind verfuegbar?
3. Welche wichtige Information liegt nur ausserhalb des Repositories oder nur implizit vor?
4. Welche Kontextluecke blockiert die naechste Autonomiestufe am staerksten?

Nicht Ziel dieses Prompts:

- ein Voll-Audit der gesamten Harness-Engine
- sofortige Umsetzung mehrerer Fixes
- reine Produktbewertung von Drift-Signalen
- Prosa-Zusammenfassungen ohne Gap-Priorisierung

## Kernvertrag

Verwende den Shared Contract aus `.github/prompts/_partials/context-engineering-contract.md` als Massstab.

- Unterscheide immer explizit zwischen **Statischem Kontext** und **Dynamischem Kontext**.
- Behaupte keine Single Source of Truth, wenn die relevante Information nur in Chat, Terminal-Historie oder Koepfen liegt.
- Markiere jede wichtige Quelle als `repo`, `extern-oeffentlich`, `extern-vertraulich` oder `hypothese`.
- Wenn Freshness unklar ist, nenne das als Luecke statt implizit von Aktualitaet auszugehen.

## Erwartete Eingaben

Lies zuerst die kleinste Menge an Quellen, die diese Fragen trennscharf beantworten kann.

Pflichtanker:

- `AGENTS.md`
- `DEVELOPER.md`
- `.github/copilot-instructions.md`
- `docs/agent-harness-golden-principles.md`
- `scripts/check_agent_harness_contract.py`
- `tests/test_agent_harness_contract.py`

Optionale Vertiefung nur bei Bedarf:

- `.github/prompts/README.md`
- relevante Audit-Dateien unter `audit/`
- bestehende Repro-Bundles, Session-Artefakte oder Harness-Reports
- aktuelle Check-, Test- oder CI-Ausgaben, sofern repo-lokal oder ueber vorhandene Tools erreichbar

## Pflichtausgabe Vor Einer Tieferen Analyse

Gib vor einem breiteren Scan genau diese vier Punkte aus:

1. Startanker im Repository
2. lokale Hypothese ueber die groesste Kontextluecke
3. billigster Check, der diese Hypothese widerlegen kann
4. welche Information wahrscheinlich ausserhalb des Repositories fehlt

Wenn du diese vier Punkte nicht sauber benennen kannst, lies noch genau eine weitere Quelle statt breit zu suchen.

## Artefakte

Erstelle Artefakte unter `work_artifacts/context_engineering_<YYYY-MM-DD>/`:

1. `context_map.md` — statische und dynamische Quellen mit Quellenklasse, Freshness und Einstiegspunkt
2. `context_gaps.md` — priorisierte Luecken, jeweils mit Auswirkung und vorgeschlagenem Hebel
3. `freshness_status.md` — was aktuell, unklar, veraltet oder nur implizit ist
4. `context_engineering_report.md` — knapper Abschluss mit Priorisierung und naechstem Schritt

Wenn keine neuen Artefakte noetig sind, begruende im Abschlussbericht, warum eine direkte Folgeumsetzung ueber `drift-context-engineering-followup.prompt.md` guenstiger ist.

## Workflow

1. **Startanker und Hypothese.** Lies die Pflichtanker, nenne Startanker, lokale Hypothese, billigsten Check und wahrscheinliche externe Luecke.
2. **Statischen Kontext kartieren.** Erfasse Maps, Docs, Schemas, Contracts und versionierte Wissensquellen. Markiere tote Enden, Doppelquellen und Wissensinseln.
3. **Dynamischen Kontext pruefen.** Pruefe Working-Tree-Sichtbarkeit, letzten Check- oder Gate-Status, Repro-Pfade, Observability, CI/Test-Naehe und Freshness. Wenn etwas nicht repo-lokal belegbar ist, zaehlt es als Luecke.
4. **Single-Source-of-Truth-Gaps benennen.** Liste Informationen auf, die fuer Agenten relevant sind, aber nur in Chat, Terminal-Archaeologie oder externen Systemen leben.
5. **Hebeldefekte priorisieren.** Priorisiere 1 bis 3 Defekte nach Autonomieblockade, Risiko durch veralteten Kontext und billiger Falsifizierbarkeit.
6. **Route entscheiden.** Wenn der naechste Schritt Analyse bleibt, halte den Defekt im Report fest. Wenn eine schmale Umsetzung direkt moeglich ist, verweise mit Defekt-ID und Validierungsidee auf `drift-context-engineering-followup.prompt.md`.

## Bewertungslogik

Bewerte jede relevante Quelle und jede Luecke entlang dieser Fragen:

- ist sie fuer Agenten repo-lokal auffindbar?
- ist sie aktuell genug fuer eine unmittelbare Entscheidung?
- ist sie maschinenlesbar oder wenigstens klar strukturiert?
- macht sie den naechsten Schritt billiger oder nur laenger?

Priorisiere die Luecken, die Autonomie, Reproduzierbarkeit oder Recovery am staerksten blockieren.

## Typische Checks

```bash
.venv\Scripts\python.exe scripts\check_agent_harness_contract.py --root .
.venv\Scripts\python.exe -m pytest tests/test_agent_harness_contract.py -q --tb=short
```

Nutze zusaetzliche Checks nur, wenn sie die Freshness- oder Kontextfrage wirklich klaeren.

## Abschlussbericht

Nutze fuer den Abschlussbericht nur dieses Raster:

```text
- Startanker: ...
- Groesste Kontextluecke: ...
- Statischer Kontext: ausreichend | lueckig | widerspruechlich
- Dynamischer Kontext: ausreichend | lueckig | stale | unklar
- Evidenz ausserhalb des Repositories: ...
- Naechster Hebel: ...
- Route: weiterer Audit | follow-up | blockiert
```

## Done-Definition

Erfolg bedeutet: Der Zustand des statischen und dynamischen Agenten-Kontexts ist repo-lokal kartiert, die groessten Kontextluecken sind priorisiert und der naechste Hebeldefekt ist so benannt, dass er direkt in `drift-context-engineering-followup.prompt.md` oder in eine gezielte Harness-Verbesserung uebergehen kann.
