<!--
SYNC IMPACT REPORT
Version change: (blank template) → 1.0.0
Added sections: Core Principles (I–V), Technology Stack & Constraints, Development Workflow & Gates, Governance
Modified principles: n/a (first ratification)
Removed sections: n/a
Templates requiring updates:
  ✅ plan-template.md — Constitution Check gate updated with principle-derived gates
  ✅ spec-template.md — Requirements section aligned to Library-First + TDD principles
  ✅ tasks-template.md — Phase 2 foundational tasks reflect TDD and functional patterns
Follow-up TODOs: none — all placeholders resolved
-->

# Drift Constitution

## Core Principles

### I. Library-First

Every feature MUST be implemented as a standalone library first. Libraries must be
self-contained, independently testable, and carry a clear documented purpose. No
organizational-only (pass-through) libraries are permitted. Downstream consumers —
CLI commands, the MCP server, and API endpoints — integrate libraries; they MUST NOT
contain core logic themselves.

Rationale: Standalone libraries guarantee testability before integration, prevent
logic from accumulating in entry-point layers, and enable third-party reuse without
coupling to Drift's CLI or server surface.

### II. Test-First (NON-NEGOTIABLE)

TDD is strictly enforced. Tests MUST be written and approved before implementation
begins. The Red-Green-Refactor cycle is mandatory for all changes to `src/drift/`.
Skipping TDD requires explicit documented justification and Maintainer approval.

Integration tests MUST cover new library contracts, contract changes, and cross-signal
or cross-layer communication. Precision/recall fixtures in `tests/fixtures/ground_truth.py`
MUST be updated whenever a signal's detection logic changes.

Rationale: Drift's correctness guarantee (77–95% real-world precision) depends on
a verified, reproducible test corpus. TDD prevents regressions from accumulating
silently under AI-assisted edits.

### III. Functional Programming

Prefer functional programming patterns: pure functions, immutable data structures,
and composition over inheritance. Pydantic models MUST use `frozen=True` wherever
values are not meant to mutate after construction. Side effects MUST be isolated at
system boundaries (I/O, CLI entry points, Git access layers). Shared mutable state
is prohibited; use typed value objects instead.

Rationale: Pure functions are trivially unit-testable, composable, and parallelisable.
Immutability eliminates a class of cross-signal interference bugs that are otherwise
invisible to static analysis.

### IV. CLI Interface & Observability

Every library MUST expose its functionality via a Click subcommand. Text I/O protocol:
stdin/args → stdout, errors → stderr. Both JSON and human-readable (Rich) output formats
MUST be supported for all analysis commands. Structured logging and opt-in telemetry
ensure production debuggability. SARIF output is required for CI/GitHub Actions integration.

Rationale: CLI-first design enforces a clean interface contract between library and
consumer. Dual output formats (machine + human) serve both automation pipelines and
developer workflows without compromise.

### V. Simplicity & YAGNI

Start simple. Complexity MUST be justified with concrete evidence — benchmark data,
precision/recall deltas, or a failing test that cannot be fixed otherwise. No speculative
features, no defensive abstractions for scenarios that cannot occur at system boundaries.
Every added abstraction layer must pay its cost in demonstrated readability or performance.

Rationale: Drift analyzes AI-generated code for over-engineering. Drift itself must
model the practices it enforces.

## Technology Stack & Constraints

**Language/Version**: Python 3.11+
**Package Management**: uv (`pip install -e '.[dev]'` for development installs)
**Core Dependencies**: Click (CLI), Pydantic (models, frozen=True), Rich (terminal output)
**Quality Tools**: pytest, mypy (strict), ruff (lint + format)
**Output Formats**: Rich terminal, JSON, SARIF, Markdown
**No LLM dependency**: All 24 signals are deterministic static analysis; no network
calls during analysis.
**Performance Budget**: ≤30 s for a 2900-file codebase (warm run). Regressions against
`benchmarks/perf_budget.json` block merge.
**Signals**: 24 signals across file-local and cross-file scopes (PFS, AVS, MDS, EDS,
and others). Signal logic lives exclusively in `src/drift/signals/`.

## Development Workflow & Gates

1. **Policy Gate first**: Before any implementation, the Drift Policy Gate from
   `.github/instructions/drift-policy.instructions.md` MUST be visibly output.
2. **Conventional Commits**: `feat:` / `fix:` / `chore:` / `docs:` / `test:`.
   Releases are automated via python-semantic-release in CI — no manual version bumps.
3. **Pre-push gates**: `make gate-check COMMIT_TYPE=<type>` MUST pass before push.
   Blast-radius reports are required when `src/drift/**` changes (`DRIFT_BLAST_LIVE=1`).
4. **Audit artifacts**: Changes to signals, ingestion, or output MUST update
   `audit_results/` (FMEA, STRIDE, fault trees, risk register) per POLICY.md §18.
5. **Maintainer approval required** for: ADR acceptance, scoring weight changes,
   policy amendments, and any push to remote.
6. **Post-edit nudge**: After every file edit, `drift_nudge` MUST be called as a
   fast regression detector before proceeding to the next change.

## Governance

This constitution supersedes all other development practices within this repository.
Amendments MUST increment the version according to semantic versioning (MAJOR: principle
removal or redefinition; MINOR: principle or section addition; PATCH: wording/clarification).
Every amendment MUST include a Sync Impact Report and propagate changes to all dependent
templates in `.specify/templates/`.

**Single Source of Truth**: `POLICY.md` governs product, prioritisation, and risk rules.
This constitution governs development discipline. In case of conflict, `POLICY.md` takes
precedence. Runtime developer guidance: `DEVELOPER.md`.

All PRs and code reviews MUST verify compliance with Principles I–V. Complexity that
cannot be justified against Principle V MUST be rejected regardless of test coverage.

**Version**: 1.0.0 | **Ratified**: 2026-04-27 | **Last Amended**: 2026-04-27
