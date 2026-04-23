"""Task-Type to context-path mapping.

This module is intentionally minimal: it maps task types to lists of
workspace-relative paths (the actual Single Sources of Truth).

Rules:
- Only paths. No rule text. No policy duplication.
- Each path must point to an existing file in the repository.
- Budget: max 8 paths per task type so the agent sees a small,
  actionable context list.

If a rule needs to be changed, change it in the referenced .md file —
not here. This module must never grow to contain substantive guidance.
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
