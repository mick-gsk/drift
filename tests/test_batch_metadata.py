"""Tests for fix-loop batch metadata (ADR-020).

Covers:
- Fix-template equivalence classes
- Batch metadata injection
- API response fields
- Diff signal filtering
- remaining_by_signal in fix_plan
- resolved_count_by_rule in diff
"""

from __future__ import annotations

from pathlib import PurePosixPath

from drift.models import AgentTask, Finding, Severity, SignalType  # noqa: F811
from drift.output.agent_tasks import _fix_template_class, _inject_batch_metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    signal: SignalType = SignalType.BROAD_EXCEPTION_MONOCULTURE,
    *,
    title: str = "bare except",
    file_path: str = "src/a.py",
    severity: Severity = Severity.MEDIUM,
    impact: float = 0.5,
    score: float = 0.3,
    fix: str = "Use specific exceptions",
    metadata: dict | None = None,
) -> Finding:
    return Finding(
        signal_type=signal,
        title=title,
        description="test finding",
        file_path=PurePosixPath(file_path),
        start_line=1,
        severity=severity,
        impact=impact,
        score=score,
        fix=fix,
        metadata=metadata or {},
    )


def _make_task(
    signal: SignalType = SignalType.BROAD_EXCEPTION_MONOCULTURE,
    *,
    file_path: str = "src/a.py",
    metadata: dict | None = None,
) -> AgentTask:
    return AgentTask(
        id=f"test-{file_path}",
        priority=1,
        signal_type=signal,
        severity=Severity.MEDIUM,
        title="test task",
        description="test description",
        action="fix it",
        file_path=file_path,
        start_line=1,
        symbol=None,
        related_files=[],
        complexity="low",
        automation_fit="high",
        review_risk="low",
        change_scope="single_file",
        constraints=[],
        success_criteria=["passes"],
        expected_effect="improvement",
        depends_on=[],
        metadata=metadata or {},
        repair_maturity="established",
    )


# ---------------------------------------------------------------------------
# Fix-template equivalence classes
# ---------------------------------------------------------------------------


class TestFixTemplateClass:
    def test_uniform_template_signal(self):
        """Uniform-template signals get signal-only key."""
        task = _make_task(SignalType.BROAD_EXCEPTION_MONOCULTURE)
        assert _fix_template_class(task) == "broad_exception_monoculture"

    def test_pfs_groups_by_canonical(self):
        """PFS tasks group by canonical pattern name."""
        task = _make_task(
            SignalType.PATTERN_FRAGMENTATION,
            metadata={"canonical": "factory_pattern"},
        )
        assert _fix_template_class(task) == "pattern_fragmentation:factory_pattern"

    def test_mds_groups_by_duplicate_group(self):
        """MDS tasks group by duplicate group."""
        task = _make_task(
            SignalType.MUTANT_DUPLICATE,
            metadata={"duplicate_group": "grp1"},
        )
        assert _fix_template_class(task) == "mutant_duplicate:grp1"

    def test_default_groups_by_rule_id(self):
        """Default signals group by signal:rule_id."""
        task = _make_task(
            SignalType.ARCHITECTURE_VIOLATION,
            metadata={"rule_id": "circular_dep"},
        )
        assert _fix_template_class(task) == "architecture_violation:circular_dep"

    def test_default_no_rule_id(self):
        """Without rule_id, key is just signal name."""
        task = _make_task(SignalType.ARCHITECTURE_VIOLATION, metadata={})
        assert _fix_template_class(task) == "architecture_violation"


# ---------------------------------------------------------------------------
# Batch metadata injection
# ---------------------------------------------------------------------------


class TestInjectBatchMetadata:
    def test_single_task_not_batch_eligible(self):
        """A single task in its class is not batch-eligible."""
        tasks = [_make_task(file_path="src/a.py")]
        _inject_batch_metadata(tasks)
        assert tasks[0].metadata["batch_eligible"] is False
        assert tasks[0].metadata["pattern_instance_count"] == 1

    def test_multiple_tasks_same_class_batch_eligible(self):
        """Multiple tasks in same class are batch-eligible."""
        tasks = [
            _make_task(file_path="src/a.py"),
            _make_task(file_path="src/b.py"),
            _make_task(file_path="src/c.py"),
        ]
        _inject_batch_metadata(tasks)
        for t in tasks:
            assert t.metadata["batch_eligible"] is True
            assert t.metadata["pattern_instance_count"] == 3
            assert sorted(t.metadata["affected_files_for_pattern"]) == [
                "src/a.py",
                "src/b.py",
                "src/c.py",
            ]

    def test_mixed_classes(self):
        """Tasks in different classes get independent batch metadata."""
        t_bem = _make_task(SignalType.BROAD_EXCEPTION_MONOCULTURE, file_path="src/a.py")
        t_gcd = _make_task(SignalType.GUARD_CLAUSE_DEFICIT, file_path="src/b.py")
        tasks = [t_bem, t_gcd]
        _inject_batch_metadata(tasks)
        assert t_bem.metadata["batch_eligible"] is False
        assert t_gcd.metadata["batch_eligible"] is False


# ---------------------------------------------------------------------------
# API response fields
# ---------------------------------------------------------------------------


class TestApiResponseBatchFields:
    def test_task_api_dict_includes_batch_fields(self):
        """_task_to_api_dict includes batch metadata fields."""
        from drift.api_helpers import _task_to_api_dict

        task = _make_task(metadata={
            "batch_eligible": True,
            "pattern_instance_count": 3,
            "affected_files_for_pattern": ["a.py", "b.py", "c.py"],
            "fix_template_class": "broad_exception_monoculture",
        })
        d = _task_to_api_dict(task)
        assert d["batch_eligible"] is True
        assert d["pattern_instance_count"] == 3
        assert d["affected_files_for_pattern"] == ["a.py", "b.py", "c.py"]
        assert d["fix_template_class"] == "broad_exception_monoculture"

    def test_task_api_dict_defaults_when_no_batch(self):
        """_task_to_api_dict provides defaults when batch metadata is absent."""
        from drift.api_helpers import _task_to_api_dict

        task = _make_task(metadata={})
        d = _task_to_api_dict(task)
        assert d["batch_eligible"] is False
        assert d["pattern_instance_count"] == 1
        assert d["affected_files_for_pattern"] == []
        assert d["fix_template_class"] == ""


# ---------------------------------------------------------------------------
# fix_plan agent_instruction
# ---------------------------------------------------------------------------


class TestFixPlanAgentInstruction:
    def test_batch_instruction_when_batch_eligible(self):
        """Agent instruction mentions batch workflow when batch tasks exist."""
        from drift.api import _fix_plan_agent_instruction

        task = _make_task(metadata={"batch_eligible": True})
        instruction = _fix_plan_agent_instruction([task])
        assert "batch_eligible" in instruction
        assert "affected_files_for_pattern" in instruction

    def test_default_instruction_when_no_batch(self):
        """Agent instruction is file-by-file when no batch tasks."""
        from drift.api import _fix_plan_agent_instruction

        task = _make_task(metadata={})
        instruction = _fix_plan_agent_instruction([task])
        assert "Do not batch" in instruction
