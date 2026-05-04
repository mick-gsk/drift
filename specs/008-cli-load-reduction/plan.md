# Implementation Plan: CLI Load Reduction

**Branch**: `010-before-specify-hook` | **Date**: 2026-05-02 | **Spec**: [specs/008-cli-load-reduction/spec.md](specs/008-cli-load-reduction/spec.md)
**Input**: Feature specification from `specs/008-cli-load-reduction/spec.md`

## Summary

Das Feature reduziert die kognitive Last in `drift --help`, indem die flache Liste der Top-Level-Commands in nutzerorientierte Aufgabenbereiche und klare Einstiegspfade ueberfuehrt wird. Bestehende Aufrufe bleiben kompatibel; neu ist primär die Orientierungsschicht (strukturierte Help-Ausgabe plus Fuehrung von Uebersicht zu Details).

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Click, Rich, Pydantic (fuer strukturierte Help-Modelle)  
**Storage**: N/A (rein prozessuale CLI-Ausgabe)  
**Testing**: pytest (unit, integration, CLI-contract tests)  
**Target Platform**: Cross-platform terminal usage (Windows/Linux/macOS)
**Project Type**: CLI + library slice in `packages/drift-cli/src/drift_cli/`  
**Performance Goals**: `drift --help` bleibt gefuehlt instantan; keine merkliche Zusatzlatenz durch Strukturierung  
**Constraints**: Keine Breaking Changes fuer bestehende Befehlsaufrufe; JSON/Rich-Ausgabe muss konsistent bleiben  
**Scale/Scope**: Reorganisation fuer aktuell 48 Top-Level-Kommandos mit Fokus auf Einstieg und Navigation

## Constitution Check

*GATE: Passed before Phase 0 research; re-checked after Phase 1 design.*

### Pre-Research Gate

- [x] **I. Library-First**: Help-Navigation wird als eigene Slice-Library unter `packages/drift-cli/src/drift_cli/help_nav/` modelliert; Command-Module enthalten nur Wiring.
- [x] **II. Test-First**: Umsetzung wird mit zuerst scheiternden CLI/Contract-Tests geplant; keine Implementierung in dieser Plan-Phase.
- [x] **III. Functional Programming**: Mapping von Commands zu Capability-Areas erfolgt ueber pure Funktionen und immutable Modelle.
- [x] **IV. CLI Interface & Observability**: Ausgabe bleibt ueber Click integriert und muss Rich + JSON-Pfade abdecken; zusaetzlich wird ein expliziter Slice-Subcommandpfad fuer Help-Navigation bereitgestellt und in die Root-Help-Uebersicht eingebunden.
- [x] **V. Simplicity & YAGNI**: Kein neues Persistenzsystem, keine dynamische Plugin-Engine; nur notwendige Struktur-/Navigationslogik.
- [x] **VI. Vertical Slices**: Eigenstaendige Slice geplant, keine Querschnittslogik in Fremdmodulen.

### Post-Design Re-Check

- [x] Design-Artefakte (`research.md`, `data-model.md`, `contracts/`, `quickstart.md`) halten die Slice-Grenzen ein.
- [x] Schnittstellenvertrag zeigt additive Navigation statt Verhaltensbruch bei Legacy-Aufrufen.
- [x] Testplan priorisiert Nutzerfluss (Entry Path) und Kompatibilitaet in getrennten, unabhaengig testbaren Szenarien.
- [x] CLI-Vertrag erfasst explizit Root-Help-Integration plus dedizierten Help-Nav-Subcommandpfad zur Erfuellung von Principle IV.

## Project Structure

### Documentation (this feature)

```text
specs/008-cli-load-reduction/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli-help-navigation.contract.md
└── tasks.md
```

### Source Code (repository root)

```text
packages/drift-cli/src/drift_cli/help_nav/
├── __init__.py
├── _models.py
├── _grouping.py
├── _render.py
└── _compat.py

packages/drift-cli/src/drift_cli/cli.py

tests/help_nav/
├── test_help_nav_unit.py
├── test_help_nav_contract.py
└── test_help_nav_integration.py
```

**Structure Decision**: Option 1 (Vertical Slice). Die neue Orientierungsschicht wurde als Slice `packages/drift-cli/src/drift_cli/help_nav/` umgesetzt und in `packages/drift-cli/src/drift_cli/cli.py` verdrahtet. Keine Multi-Layer-Ausweitung noetig.

## Complexity Tracking

Keine Constitution-Verletzung identifiziert; keine Ausnahmen erforderlich.

## Implementation Snapshot

- Implementiert: `packages/drift-cli/src/drift_cli/help_nav/` (`_models.py`, `_grouping.py`, `_render.py`, `_compat.py`, `__init__.py`)
- CLI-Wiring: `packages/drift-cli/src/drift_cli/cli.py` nutzt jetzt modellbasierte Help-Sektionen plus `help-nav` Subcommand
- Tests: `tests/help_nav/test_help_nav_unit.py`, `tests/help_nav/test_help_nav_contract.py`, `tests/help_nav/test_help_nav_integration.py` sind ergänzt
- Regression: bestehende Runtime-CLI-Tests bleiben gruen (`tests/test_cli_runtime.py`)
