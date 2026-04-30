"""Task-Type and Signal-ID to context-path mapping.

This module is intentionally minimal: it maps task types and signal IDs to
lists of workspace-relative paths (the actual Single Sources of Truth).

Rules:
- Only paths. No rule text. No policy duplication.
- Each path must point to an existing file in the repository.
- Budget: max 8 paths per task type, max 4 paths per signal so the agent
  sees a small, actionable context list.

If a rule needs to be changed, change it in the referenced .md file —
not here. This module must never grow to contain substantive guidance.

Just-in-time context injection (ADR-100):
SIGNAL_CONTEXT_PATHS maps signal IDs to the minimal set of context documents
an agent needs to fix that specific signal. Only the relevant slice is surfaced
per run, not the full llms.txt.
"""

from __future__ import annotations

VALID_TASK_TYPES: tuple[str, ...] = (
    "feat",
    "fix",
    "chore",
    "signal",
    "prompt",
    "review",
)

MAX_PATHS_PER_TYPE = 8

# ---------------------------------------------------------------------------
# Signal-level context manifest (just-in-time injection)
# ---------------------------------------------------------------------------

MAX_PATHS_PER_SIGNAL = 4

# Maps signal_id (lowercase, matches SignalType enum values from
# ``src/drift/models/_enums.py`` / ``src/drift/models/__init__.py``) to a
# tuple of workspace-relative paths that provide the minimal context an agent
# needs to understand and fix findings for that signal.
#
# Each entry MUST include the signal reference doc. ADRs are added only when
# they carry precision/design decisions that are not obvious from the signal
# doc alone.
SIGNAL_CONTEXT_PATHS: dict[str, tuple[str, ...]] = {
    # ── structural_risk ────────────────────────────────────────────────────
    "pattern_fragmentation": (
        "docs-site/reference/signals/pfs.md",
        "docs/decisions/ADR-019-pfs-return-pattern-extraction.md",
        "docs/decisions/ADR-049-pfs-canonical-code-snippet.md",
    ),
    "mutant_duplicate": (
        "docs-site/reference/signals/mds.md",
        "docs/decisions/ADR-014-mds-precision-first-scoring-readiness.md",
        "docs/decisions/ADR-038-mds-name-distance-and-protocol-awareness.md",
    ),
    "bypass_accumulation": (
        "docs-site/reference/signals/bat.md",
    ),
    "exception_contract_drift": (
        "docs-site/reference/signals/ecm.md",
    ),
    "system_misalignment": (
        "docs-site/reference/signals/sms.md",
    ),
    "test_polarity_deficit": (
        "docs-site/reference/signals/tpd.md",
    ),
    "temporal_volatility": (
        "docs-site/reference/signals/tvs.md",
    ),
    "ts_architecture": (
        "docs-site/reference/signals/tsa.md",
    ),
    # ── architecture_boundary ──────────────────────────────────────────────
    "architecture_violation": (
        "docs-site/reference/signals/avs.md",
        "docs/decisions/ADR-036-avs-models-omnilayer-and-configurable-dirs.md",
        "docs/decisions/ADR-044-architecture-boundary-presets.md",
    ),
    "circular_import": (
        "docs-site/reference/signals/cir.md",
    ),
    "co_change_coupling": (
        "docs-site/reference/signals/ccc.md",
        "docs/decisions/ADR-051-ccc-commit-context-test-template.md",
    ),
    "cohesion_deficit": (
        "docs-site/reference/signals/cod.md",
    ),
    "fan_out_explosion": (
        "docs-site/reference/signals/foe.md",
    ),
    # ── style_hygiene ──────────────────────────────────────────────────────
    "naming_contract_violation": (
        "docs-site/reference/signals/nbv.md",
        "docs/decisions/ADR-012-copilot-context-actionability-pfs-nbv.md",
    ),
    "doc_impl_drift": (
        "docs-site/reference/signals/dia.md",
        "docs/decisions/ADR-017-dia-false-positive-reduction.md",
        "docs/decisions/ADR-037-dia-configurable-auxiliary-dirs-and-keywords.md",
    ),
    "explainability_deficit": (
        "docs-site/reference/signals/eds.md",
        "docs/decisions/ADR-048-eds-exposition-filter.md",
    ),
    "broad_exception_monoculture": (
        "docs-site/reference/signals/bem.md",
    ),
    "guard_clause_deficit": (
        "docs-site/reference/signals/gcd.md",
    ),
    "dead_code_accumulation": (
        "docs-site/reference/signals/dca.md",
    ),
    "cognitive_complexity": (
        "docs-site/reference/signals/cxs.md",
    ),
    # ── security ───────────────────────────────────────────────────────────
    "missing_authorization": (
        "docs-site/reference/signals/maz.md",
        "docs/decisions/ADR-016-security-signals-wave2-calibration.md",
    ),
    "insecure_default": (
        "docs-site/reference/signals/isd.md",
    ),
    "hardcoded_secret": (
        "docs-site/reference/signals/hsc.md",
        "docs/decisions/ADR-056-hsc-fp-reduction-env-marker-fixtures.md",
    ),
    # ── ai_quality ─────────────────────────────────────────────────────────
    "phantom_reference": (
        "docs-site/reference/signals/phr.md",
        "docs/decisions/ADR-033-phantom-reference-signal.md",
        "docs/decisions/ADR-040-phr-import-resolver.md",
    ),
}

CONTEXT_PATHS: dict[str, tuple[str, ...]] = {
    "feat": (
        ".github/instructions/drift-policy.instructions.md",
        ".github/instructions/drift-push-gates.instructions.md",
        ".github/instructions/drift-agent-quickref.instructions.md",
        ".github/skills/drift-commit-push/SKILL.md",
        ".github/skills/drift-evidence-artifact-authoring/SKILL.md",
    ),
    "fix": (
        ".github/instructions/drift-policy.instructions.md",
        ".github/instructions/drift-push-gates.instructions.md",
        ".github/instructions/drift-agent-quickref.instructions.md",
        ".github/skills/drift-commit-push/SKILL.md",
    ),
    "chore": (
        ".github/instructions/drift-push-gates.instructions.md",
        ".github/instructions/drift-agent-quickref.instructions.md",
        ".github/skills/drift-dependency-update/SKILL.md",
    ),
    "signal": (
        ".github/instructions/drift-policy.instructions.md",
        ".github/instructions/drift-push-gates.instructions.md",
        ".github/skills/drift-signal-development-full-lifecycle/SKILL.md",
        ".github/skills/drift-risk-audit-artifact-updates/SKILL.md",
        ".github/skills/drift-adr-workflow/SKILL.md",
        ".github/skills/drift-ground-truth-fixture-development/SKILL.md",
    ),
    "prompt": (
        ".github/instructions/drift-policy.instructions.md",
        ".github/instructions/drift-prompt-engineering.instructions.md",
        ".github/skills/drift-agent-prompt-authoring/SKILL.md",
        ".github/prompts/_partials/konventionen.md",
    ),
    "review": (
        ".github/instructions/drift-quality-workflow.instructions.md",
        ".github/prompts/_partials/review-checkliste.md",
        ".github/skills/drift-pr-review/SKILL.md",
    ),
}


def context_for(task_type: str) -> tuple[str, ...]:
    """Return the context path tuple for a task type.

    Raises:
        KeyError: If task_type is not a valid task type.
    """
    if task_type not in CONTEXT_PATHS:
        raise KeyError(task_type)
    return CONTEXT_PATHS[task_type]


def signal_context_for(signal_id: str) -> tuple[str, ...]:
    """Return the context path tuple for a signal ID.

    Returns the minimal set of documentation paths an agent needs to
    understand and fix findings for the given signal. Only mapped signals
    return a non-empty tuple; unmapped signals return an empty tuple rather
    than raising, so callers can safely iterate without special-casing.

    Args:
        signal_id: Lowercase signal identifier matching the SignalType enum
            value (e.g. ``'architecture_violation'``, ``'pattern_fragmentation'``).

    Returns:
        Tuple of workspace-relative paths (may be empty if the signal has
        no dedicated mapping yet).
    """
    return SIGNAL_CONTEXT_PATHS.get(signal_id, ())
