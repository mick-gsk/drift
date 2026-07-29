# Drift Agent Guard — Ergebnis

**Datum:** 2026-07-29 · **Branch:** `feat/agent-guard` · **Basis:** `origin/main` @ `6fecb263`

Jede Zahl unten stammt aus einem Kommando, dessen Ausgabe im Terminal stand.
Keine geschätzten, gerundeten oder erinnerten Werte.

---

## Gates

| Gate | Schwelle | Vorher | Nachher | Status |
|---|---|---|---|---|
| G1 Latenz `pre` p95 | ≤ 150 ms | existierte nicht | 49,79 ms (Fixture) · 71,51 ms (dieses Repo) | PASS |
| G1 Latenz `post` p95 | ≤ 150 ms | existierte nicht | 52,16 ms (Fixture) · 87,35 ms (dieses Repo) | PASS |
| G2 Import-Hygiene | 0 schwere Module | 13 über `drift.cli` | 0 | PASS |
| G3 Recall auf Ground Truth | ≥ 90 % | 0 % (Vertrag war leer) | 100 % (3/3) | PASS |
| G3 Falschmeldungen auf sauberen Dateien | 0 | 0 | 0 (3 Dateien) | PASS |
| G4 Oberfläche | ≤ 1 MCP-Server, ≤ 2 Commands | 47 CLI-Commands | 0 MCP-Server, 2 Commands | PASS |
| G5 Install → Guard aktiv | ≤ 60 s | existierte nicht | 5 s | PASS |
| G6 Index-Bau (drift-Repo) | ≤ 120 s | 214–462 s **pro Ein-Datei-Prüfung** | 5,9 s **einmalig**, inkrementell < 2 s | PASS |
| G7 Zähler-Ehrlichkeit | Test grün | existierte nicht | grün | PASS |

`python scripts/gates/run_all_gates.py` → `all gates passed`, Exit 0.

## Referenzmessungen

`benchmark_results/guard_baseline.json` — dieselbe Messfunktion vorher und nachher,
je 20 Läufe, kalt, macOS/arm64, Python 3.12.13:

| Aufruf | p50 | p95 |
|---|---|---|
| `import drift.cli` (der Pfad, den der Guard meidet) | 3229 ms | 3959 ms |
| `drift --help` | 3243 ms | 3480 ms |
| `python -c "import sqlite3, ast, json"` (Boden) | 24 ms | 29 ms |
| `drift-guard pre` (dieses Repo, 344 Dateien) | 70 ms | 72 ms |
| `drift-guard post` (dieses Repo, 344 Dateien) | 86 ms | 87 ms |

Der Guard liegt damit rund **45× unter** dem Aufruf, den er ersetzt, und etwa
2,5–3× über dem, was der Python-Start allein kostet.

## Testsuite

`pytest tests -q -m "not slow"` → **6849 passed, 6 skipped, 0 failed** (335 s),
davon 66 im Guard. `ruff check src tests` → clean. `mypy src` → 351 Dateien, keine Fehler.

## Live in Claude Code verifiziert

Mit isoliertem `CLAUDE_CONFIG_DIR`, damit die echte Installation unberührt bleibt:

```
Read hooks.json for plugin drift (enabled=true)
Registered 4 hooks from 1 plugins
Loaded 2 commands from plugin drift default directory
Successfully parsed and validated hook JSON output
Hook SessionStart ("${CLAUDE_PLUGIN_ROOT}/hooks/guard-session-start.sh")
  provided additionalContext (282 chars)
```

`claude plugin validate .claude-plugin/plugin.json --strict` → passed.
`claude plugin validate .claude-plugin/marketplace.json --strict` → passed.

**Nicht verifiziert:** ein echter Modell-Zug. Die isolierte Config hat keine
Anmeldedaten, und die echte Config anzufassen wäre ein Eingriff in die laufende
Umgebung des Nutzers gewesen. `PreToolUse`, `PostToolUse` und `Stop` sind
stattdessen durch Tests abgedeckt, die die realen Hook-Skripte mit realen
Payloads ausführen und die Hülle prüfen.

## Zwei Korrekturen, die während der Umsetzung nötig wurden

**Die Hooks erreichten das Modell nicht.** Sie schrieben ihre Funde nach stdout
und beendeten sich mit 0. Für `PreToolUse` und `PostToolUse` landet das
ausschließlich im Transcript — das Modell sieht es nie. Das Kernversprechen wäre
still ausgefallen, und zwar so, dass es beim Ausprobieren wie „findet halt
nichts" ausgesehen hätte. Der Weg ins Modell ist
`hookSpecificOutput.additionalContext`; die Sessionbilanz geht getrennt über
`systemMessage`, weil sie an den Menschen gerichtet ist.

**Ein zweiter Interpreter pro Edit.** Die Hook-Skripte parsten
`tool_input.file_path` in Bash über `python3 -c`. Das ist ein kompletter
Interpreter-Start innerhalb eines 150-ms-Budgets, für ein einziges JSON-Feld.
Der Guard liest die Payload jetzt selbst (`--payload-stdin`); die Shell-Wrapper
sind vier Zeilen.

## Was bewusst offen blieb

- **Outcome-Validierung des drift-Scores** — unverändert offen (Spec §7). Der
  Guard behauptet nicht, dass ein niedrigerer Score besser ist; er meldet, was
  im Repo existiert, und überlässt die Bewertung dem Leser.
- **`drift self` segfaultet** ([#771](https://github.com/mick-gsk/drift/issues/771)).
  Nicht Teil dieses Vorhabens, aber dabei gefunden und mit minimalem Repro belegt:
  `analyze_repo(root, cfg, target_path="src/drift")` stürzt ab, ohne `target_path`
  läuft dieselbe Analyse durch.
- **Reduktion der 47 CLI-Commands und 60 CI-Workflows** — nicht angefasst. Der
  Plan hat eine neue, schmale Tür gebaut, statt die alte umzubauen.
- **Weitere Plattformen** (Cursor, Copilot, Codex) — der Guard ist ein CLI mit
  JSON-Ausgabe, die Anbindung wäre je ein Manifest. Nicht gebaut, weil kein
  Nutzer sie bisher verlangt hat.
- **Andere Sprachen als Python** — `extract.py` liest Python mit `ast`. Steht so
  auf der ersten README-Seite, damit es niemand erst nach der Installation merkt.
