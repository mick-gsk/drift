"""Agent-tasks output format — translates findings into machine-readable repair tasks."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from drift import __version__
from drift.models import AgentTask, Finding, RepoAnalysis, Severity, SignalType
from drift.recommendations import Recommendation, generate_recommendations

# ---------------------------------------------------------------------------
# Deterministic task ID
# ---------------------------------------------------------------------------

_SIGNAL_PREFIX = {
    SignalType.PATTERN_FRAGMENTATION: "pfs",
    SignalType.ARCHITECTURE_VIOLATION: "avs",
    SignalType.MUTANT_DUPLICATE: "mds",
    SignalType.EXPLAINABILITY_DEFICIT: "eds",
    SignalType.TEMPORAL_VOLATILITY: "tvs",
    SignalType.SYSTEM_MISALIGNMENT: "sms",
}


def _task_id(finding: Finding) -> str:
    """Generate a deterministic, human-readable task ID."""
    prefix = _SIGNAL_PREFIX.get(finding.signal_type, finding.signal_type.value[:3])
    fp = finding.file_path.as_posix() if finding.file_path else ""
    blob = f"{finding.signal_type.value}:{fp}:{finding.title}"
    short_hash = hashlib.sha256(blob.encode()).hexdigest()[:10]
    return f"{prefix}-{short_hash}"


# ---------------------------------------------------------------------------
# Signal-specific success criteria
# ---------------------------------------------------------------------------


def _success_criteria_for(finding: Finding) -> list[str]:
    """Return machine-verifiable success criteria for a finding."""
    st = finding.signal_type
    meta = finding.metadata
    path_str = finding.file_path.as_posix() if finding.file_path else "the affected module"

    base = ["All existing tests pass after the change"]

    if st == SignalType.PATTERN_FRAGMENTATION:
        module = meta.get("module", path_str)
        return [
            f"Pattern variants in {module} reduced to 1 (canonical)",
            f"`drift analyze` reports no pattern_fragmentation finding for {module}",
            *base,
        ]

    if st == SignalType.ARCHITECTURE_VIOLATION:
        if "circular" in finding.title.lower():
            cycle = meta.get("cycle", [])
            cycle_str = " → ".join(str(c) for c in cycle[:5])
            return [
                f"Circular dependency resolved: no cycle between {cycle_str}",
                "`drift analyze` reports no circular dependency for these modules",
                *base,
            ]
        if "blast" in finding.title.lower():
            return [
                f"Blast radius of {path_str} reduced below threshold",
                "`drift analyze` reports no blast_radius finding for this module",
                *base,
            ]
        # layer violation
        return [
            f"No upward layer import from {path_str}",
            "`drift analyze` reports no layer violation for this file",
            *base,
        ]

    if st == SignalType.MUTANT_DUPLICATE:
        func_a = meta.get("function_a", "?")
        func_b = meta.get("function_b", "?")
        return [
            f"Functions '{func_a}' and '{func_b}' merged into a single implementation",
            "No mutant_duplicate finding for these functions in `drift analyze`",
            *base,
        ]

    if st == SignalType.EXPLAINABILITY_DEFICIT:
        func_name = meta.get("function_name", "?")
        criteria = [*base]
        if not meta.get("has_docstring", True):
            criteria.insert(0, f"Function '{func_name}' has a docstring")
        if not meta.get("has_return_type", True):
            criteria.insert(0, f"Function '{func_name}' has a return type annotation")
        if meta.get("complexity", 0) > 10:
            criteria.insert(
                0, f"Function '{func_name}' complexity ≤ 10 or split into sub-functions"
            )
        return criteria

    if st == SignalType.TEMPORAL_VOLATILITY:
        return [
            f"Integration tests exist for {path_str}",
            "Module churn stabilized (no unnecessary refactoring commits)",
            *base,
        ]

    if st == SignalType.SYSTEM_MISALIGNMENT:
        novel = meta.get("novel_imports", meta.get("novel_dependencies", []))
        dep_str = ", ".join(str(d) for d in novel[:5]) if novel else "novel dependencies"
        return [
            f"Dependencies ({dep_str}) documented or moved to appropriate module",
            *base,
        ]

    return base


# ---------------------------------------------------------------------------
# Signal-specific expected effect
# ---------------------------------------------------------------------------


def _expected_effect_for(finding: Finding) -> str:
    """Describe the expected structural improvement."""
    st = finding.signal_type
    meta = finding.metadata

    if st == SignalType.PATTERN_FRAGMENTATION:
        variants = meta.get("variant_count", 0)
        module = meta.get("module", "the module")
        return (
            f"Reduces pattern variants from {variants} to 1 in {module}, "
            f"lowering PFS signal contribution to the drift score"
        )

    if st == SignalType.ARCHITECTURE_VIOLATION:
        if "circular" in finding.title.lower():
            return "Eliminates circular dependency, enabling independent module evolution"
        if "blast" in finding.title.lower():
            return "Reduces blast radius, limiting change propagation across the codebase"
        return "Restores layer boundary, preventing upward coupling"

    if st == SignalType.MUTANT_DUPLICATE:
        sim = meta.get("similarity", 0.0)
        return f"Eliminates near-duplicate ({sim:.0%} similar), reducing maintenance surface"

    if st == SignalType.EXPLAINABILITY_DEFICIT:
        return "Improves code explainability, reducing onboarding cost and review friction"

    if st == SignalType.TEMPORAL_VOLATILITY:
        return "Stabilizes a high-churn module, reducing regression risk"

    if st == SignalType.SYSTEM_MISALIGNMENT:
        return "Aligns dependencies with established module patterns"

    return "Reduces architectural drift score"


# ---------------------------------------------------------------------------
# Dependency computation
# ---------------------------------------------------------------------------


def _compute_dependencies(tasks: list[AgentTask]) -> None:
    """Set intra-module depends_on edges (mutates tasks in place).

    Rule: AVS circular-dependency tasks block AVS blast-radius / layer tasks
    in the same module (solving the cycle first makes other fixes feasible).
    """
    # Index circular-dep task IDs by their module path
    circular_ids_by_module: dict[str, list[str]] = {}
    for t in tasks:
        if (
            t.signal_type == SignalType.ARCHITECTURE_VIOLATION
            and "circular" in t.title.lower()
            and t.file_path
        ):
            module = str(t.file_path).rsplit("/", 1)[0] if "/" in str(t.file_path) else ""
            circular_ids_by_module.setdefault(module, []).append(t.id)

    if not circular_ids_by_module:
        return

    for t in tasks:
        if (
            t.signal_type == SignalType.ARCHITECTURE_VIOLATION
            and "circular" not in t.title.lower()
            and t.file_path
        ):
            module = str(t.file_path).rsplit("/", 1)[0] if "/" in str(t.file_path) else ""
            deps = circular_ids_by_module.get(module, [])
            if deps:
                t.depends_on = [d for d in deps if d != t.id]


# ---------------------------------------------------------------------------
# Severity to numeric weight for priority calculation
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHT = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


# ---------------------------------------------------------------------------
# Core translation
# ---------------------------------------------------------------------------


def _finding_to_task(
    finding: Finding,
    rec: Recommendation | None,
    priority: int,
) -> AgentTask:
    """Translate a Finding + optional Recommendation into an AgentTask."""
    # Action: prefer recommendation description, fall back to finding.fix
    if rec:
        action = rec.description
        complexity = rec.effort
    elif finding.fix:
        action = finding.fix
        complexity = "medium"
    else:
        action = f"Address: {finding.description}"
        complexity = "medium"

    return AgentTask(
        id=_task_id(finding),
        signal_type=finding.signal_type,
        severity=finding.severity,
        priority=priority,
        title=finding.title,
        description=finding.description,
        action=action,
        file_path=finding.file_path.as_posix() if finding.file_path else None,
        start_line=finding.start_line,
        end_line=finding.end_line,
        related_files=[rf.as_posix() for rf in finding.related_files],
        complexity=complexity,
        expected_effect=_expected_effect_for(finding),
        success_criteria=_success_criteria_for(finding),
        metadata={
            k: v
            for k, v in finding.metadata.items()
            if k not in ("ast_fingerprint", "body_hash")
        },
    )


def analysis_to_agent_tasks(analysis: RepoAnalysis) -> list[AgentTask]:
    """Convert analysis findings into a prioritized list of agent tasks.

    Only findings with recommendation coverage are included (report-only
    signals without recommenders are excluded — they don't yet have
    actionable remediation patterns).
    """
    # Generate recommendations (keyed by finding title for matching)
    recs = generate_recommendations(analysis.findings, max_recommendations=9999)
    rec_by_title: dict[str, Recommendation] = {}
    for r in recs:
        if r.related_findings:
            for f in r.related_findings:
                rec_by_title[f.title] = r

    # Sort findings: severity weight × impact, descending
    scored = sorted(
        analysis.findings,
        key=lambda f: (_SEVERITY_WEIGHT.get(f.severity, 0) * max(f.impact, f.score)),
        reverse=True,
    )

    tasks: list[AgentTask] = []
    seen_ids: set[str] = set()
    priority = 0

    for finding in scored:
        rec = rec_by_title.get(finding.title)

        # Skip findings without recommendation coverage AND without fix text
        if rec is None and not finding.fix:
            continue

        tid = _task_id(finding)
        if tid in seen_ids:
            continue
        seen_ids.add(tid)

        priority += 1
        tasks.append(_finding_to_task(finding, rec, priority))

    # Compute intra-module dependencies
    _compute_dependencies(tasks)

    return tasks


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def _task_to_dict(t: AgentTask) -> dict[str, Any]:
    return {
        "id": t.id,
        "signal_type": t.signal_type.value,
        "severity": t.severity.value,
        "priority": t.priority,
        "title": t.title,
        "description": t.description,
        "action": t.action,
        "file_path": t.file_path,
        "start_line": t.start_line,
        "end_line": t.end_line,
        "related_files": t.related_files,
        "complexity": t.complexity,
        "expected_effect": t.expected_effect,
        "success_criteria": t.success_criteria,
        "depends_on": t.depends_on,
        "metadata": t.metadata,
    }


def analysis_to_agent_tasks_json(analysis: RepoAnalysis, indent: int = 2) -> str:
    """Serialize a RepoAnalysis to agent-tasks JSON."""
    tasks = analysis_to_agent_tasks(analysis)

    data: dict[str, Any] = {
        "version": __version__,
        "schema": "agent-tasks-v1",
        "repo": analysis.repo_path.as_posix(),
        "analyzed_at": analysis.analyzed_at.isoformat(),
        "drift_score": analysis.drift_score,
        "severity": analysis.severity.value,
        "task_count": len(tasks),
        "tasks": [_task_to_dict(t) for t in tasks],
    }

    return json.dumps(data, indent=indent, default=str)
