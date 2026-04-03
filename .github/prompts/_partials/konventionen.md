# Shared Konventionen für Drift-Prompts

> **Single Source of Truth** — Alle Prompts in `.github/prompts/` folgen diesen Konventionen.

## Policy-Gate-Pflicht

Vor der Ausführung eines Prompts MUSS der Agent das Drift Policy Gate durchlaufen
(siehe `.github/instructions/drift-policy.instructions.md`):

```
### Drift Policy Gate
- Aufgabe: [Kurzbeschreibung]
- Zulassungskriterium erfüllt: [JA / NEIN] → [welches Kriterium]
- Ausschlusskriterium ausgelöst: [JA / NEIN] → [falls JA: welches]
- Roadmap-Phase: [1 / 2 / 3 / 4] — blockiert durch höhere Phase: [JA / NEIN]
- Betrifft Signal/Architektur (§18): [JA / NEIN] → falls JA: Audit-Artefakte aktualisiert: [welche]
- Entscheidung: [ZULÄSSIG / ABBRUCH]
- Begründung: [ein Satz]
```

Bei ABBRUCH: keine Ausführung des Prompts.

## Datumsformat

Überall wo `<DATE>` oder `<DATUM>` steht: **ISO 8601** verwenden → `YYYY-MM-DD` (z.B. `2026-04-03`).

## Artefakt-Verzeichnisse

Alle Prompt-Artefakte werden unter `work_artifacts/` abgelegt:

```
work_artifacts/<prompt-kürzel>_<YYYY-MM-DD>/
```

Beispiele:
- `work_artifacts/agent_ux_2026-04-03/`
- `work_artifacts/ci_gate_2026-04-03/`
- `work_artifacts/signal_quality_2026-04-03/`

## Sandbox-Erstellung

Wenn ein Prompt eine Sandbox benötigt:

```bash
mkdir -p work_artifacts/<prompt-kürzel>_<YYYY-MM-DD>/sandbox
cd work_artifacts/<prompt-kürzel>_<YYYY-MM-DD>/sandbox
git init
# Minimal-Python-Datei für Tests:
echo "def example(): pass" > main.py
git add . && git commit -m "init"
```

## Bewertungs-Labels

Ausschließlich Labels aus `_partials/bewertungs-taxonomie.md` verwenden.
Keine Prompt-spezifischen Bewertungssysteme einführen.

## Issue-Filing

Bei GitHub-Issue-Erstellung den Template-Block aus `_partials/issue-filing.md` verwenden.
Keine individuellen Issue-Templates pro Prompt.

## Querverweise

Jeder Prompt SOLLTE am Ende seines Frontmatter-Bereichs oder in einem dedizierten Abschnitt
die relevanten Instructions, Skills und verwandten Prompts referenzieren:

- `Relevante Instructions:` — z.B. `drift-policy.instructions.md`, `drift-push-gates.instructions.md`
- `Relevanter Skill:` — z.B. `drift-pr-review/SKILL.md`, `drift-release/SKILL.md`
- `Verwandte Prompts:` — z.B. `drift-ci-gate.prompt.md`, `drift-signal-quality.prompt.md`

## Modellbezug

Prompts sind modellunabhängig formuliert. Keine Referenzen auf spezifische Modellversionen
in `description`-Feldern oder im Fließtext.
