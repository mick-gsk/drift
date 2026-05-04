from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "outcome_first_validation.py"


def load_module() -> Any:
    spec = importlib.util.spec_from_file_location("outcome_first_validation", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["outcome_first_validation"] = module
    spec.loader.exec_module(module)
    return module


def test_manifest_requires_exclusion_reason_when_excluded() -> None:
    module = load_module()
    with pytest.raises(ValueError, match="exclusion_reason"):
        module.manifest_entry_from_dict(
            {
                "task_id": "T-1",
                "cohort": "control",
                "repo": "mick-gsk/drift",
                "task_type": "bugfix",
                "outcome_hypothesis": "Should reduce steps",
                "started_at": "2026-05-01T10:00:00+00:00",
                "include_in_study": False,
            }
        )


def test_validate_manifest_records_rejects_cohort_mismatch() -> None:
    module = load_module()
    manifest = [
        module.manifest_entry_from_dict(
            {
                "task_id": "T-1",
                "cohort": "drift_informed",
                "repo": "mick-gsk/drift",
                "task_type": "feature",
                "outcome_hypothesis": "Should reduce rework",
                "started_at": "2026-05-01T10:00:00+00:00",
            }
        )
    ]
    records = [
        module.task_record_from_dict(
            {
                "task_id": "T-1",
                "cohort": "control",
                "steps_to_completion": 5,
                "rework_events": 0,
                "first_pass_success": True,
                "post_completion_defect": False,
                "completion_state": "completed",
            }
        )
    ]
    with pytest.raises(ValueError, match="cohort mismatch"):
        module.validate_manifest_records(manifest, records)


def test_compute_cohort_metrics_ignores_non_completed_records() -> None:
    module = load_module()
    records = [
        module.task_record_from_dict(
            {
                "task_id": "A",
                "cohort": "control",
                "steps_to_completion": 8,
                "rework_events": 1,
                "first_pass_success": False,
                "post_completion_defect": True,
                "completion_state": "failed",
            }
        ),
        module.task_record_from_dict(
            {
                "task_id": "B",
                "cohort": "drift_informed",
                "steps_to_completion": 4,
                "rework_events": 0,
                "first_pass_success": True,
                "post_completion_defect": False,
                "completion_state": "completed",
            }
        ),
    ]
    metrics = module.compute_cohort_metrics(records)
    assert metrics["control"].sample_size == 0
    assert metrics["drift_informed"].sample_size == 1
    assert metrics["drift_informed"].median_steps_to_completion == 4.0


def test_evaluate_go_no_go_requires_two_improvements_and_no_defect_regression() -> None:
    module = load_module()
    metrics = {
        "control": module.CohortMetrics(
            cohort="control",
            sample_size=10,
            median_steps_to_completion=10.0,
            rework_rate=0.5,
            first_pass_success_rate=0.4,
            post_completion_defect_rate=0.1,
        ),
        "drift_informed": module.CohortMetrics(
            cohort="drift_informed",
            sample_size=10,
            median_steps_to_completion=7.0,
            rework_rate=0.3,
            first_pass_success_rate=0.6,
            post_completion_defect_rate=0.1,
        ),
    }
    verdict = module.evaluate_go_no_go(metrics)
    assert verdict["decision"] == "go"
    assert verdict["passes"] == {
        "steps": True,
        "rework": True,
        "first_pass": True,
        "defects_not_worse": True,
    }


def test_evaluate_go_no_go_blocks_when_defects_worsen() -> None:
    module = load_module()
    metrics = {
        "control": module.CohortMetrics(
            cohort="control",
            sample_size=10,
            median_steps_to_completion=10.0,
            rework_rate=0.5,
            first_pass_success_rate=0.4,
            post_completion_defect_rate=0.1,
        ),
        "drift_informed": module.CohortMetrics(
            cohort="drift_informed",
            sample_size=10,
            median_steps_to_completion=6.0,
            rework_rate=0.2,
            first_pass_success_rate=0.7,
            post_completion_defect_rate=0.2,
        ),
    }
    verdict = module.evaluate_go_no_go(metrics)
    assert verdict["decision"] == "no_go"
    assert verdict["passes"]["defects_not_worse"] is False


def test_cmd_report_writes_aggregated_json(tmp_path: Path) -> None:
    module = load_module()
    manifest_path = tmp_path / "manifest.json"
    records_path = tmp_path / "records.json"
    output_path = tmp_path / "report.json"

    manifest_path.write_text(
        json.dumps(
            {
                "tasks": [
                    {
                        "task_id": "T-1",
                        "cohort": "control",
                        "repo": "mick-gsk/drift",
                        "task_type": "feature",
                        "outcome_hypothesis": "Baseline",
                        "started_at": "2026-05-01T10:00:00+00:00",
                    },
                    {
                        "task_id": "T-2",
                        "cohort": "drift_informed",
                        "repo": "mick-gsk/drift",
                        "task_type": "feature",
                        "outcome_hypothesis": "Reduce rework",
                        "started_at": "2026-05-01T11:00:00+00:00",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    records_path.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "task_id": "T-1",
                        "cohort": "control",
                        "steps_to_completion": 10,
                        "rework_events": 1,
                        "first_pass_success": False,
                        "post_completion_defect": False,
                        "completion_state": "completed",
                    },
                    {
                        "task_id": "T-2",
                        "cohort": "drift_informed",
                        "steps_to_completion": 6,
                        "rework_events": 0,
                        "first_pass_success": True,
                        "post_completion_defect": False,
                        "completion_state": "completed",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = module.main(
        [
            "report",
            "--manifest",
            str(manifest_path),
            "--records",
            str(records_path),
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["schema_version"] == "1.0"
    assert report["verdict"]["decision"] == "go"
    assert report["cohort_metrics"]["control"]["median_steps_to_completion"] == 10.0
    assert (
        report["cohort_metrics"]["drift_informed"]["first_pass_success_rate"] == 1.0
    )


# ---------------------------------------------------------------------------
# session_summary_to_task_record
# ---------------------------------------------------------------------------


def _make_session_summary(
    *,
    tool_calls: int = 10,
    plans_invalidated: int = 0,
    nudge_degrading: int = 0,
    tasks_completed: int = 3,
    tasks_failed: int = 0,
) -> dict:
    return {
        "tool_calls": tool_calls,
        "task_queue": {
            "total": 3,
            "completed": tasks_completed,
            "claimed": 3,
            "failed": tasks_failed,
            "remaining": 0,
        },
        "orchestration_metrics": {
            "plans_invalidated": plans_invalidated,
            "nudge_degrading": nudge_degrading,
        },
    }


def test_session_summary_maps_tool_calls_to_steps() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(tool_calls=7),
        task_id="S-1",
        cohort="drift_informed",
    )
    assert record.steps_to_completion == 7


def test_session_summary_rework_is_sum_of_invalidated_and_degrading() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(plans_invalidated=1, nudge_degrading=2),
        task_id="S-2",
        cohort="control",
    )
    assert record.rework_events == 3
    assert record.first_pass_success is False


def test_session_summary_first_pass_true_when_no_rework() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(),
        task_id="S-3",
        cohort="drift_informed",
    )
    assert record.rework_events == 0
    assert record.first_pass_success is True


def test_session_summary_completion_state_failed_when_no_completions() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(tasks_completed=0, tasks_failed=1),
        task_id="S-4",
        cohort="control",
    )
    assert record.completion_state == "failed"


def test_session_summary_post_completion_defect_default_false() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(),
        task_id="S-5",
        cohort="drift_informed",
    )
    assert record.post_completion_defect is False


def test_session_summary_post_completion_defect_can_be_set() -> None:
    module = load_module()
    record = module.session_summary_to_task_record(
        _make_session_summary(),
        task_id="S-6",
        cohort="control",
        post_completion_defect=True,
    )
    assert record.post_completion_defect is True


# ---------------------------------------------------------------------------
# append_record + ingest-session CLI
# ---------------------------------------------------------------------------


def test_append_record_creates_file_on_first_call(tmp_path: Path) -> None:
    module = load_module()
    records_path = tmp_path / "records.json"
    record = module.task_record_from_dict(
        {
            "task_id": "R-1",
            "cohort": "drift_informed",
            "steps_to_completion": 5,
            "rework_events": 0,
            "first_pass_success": True,
            "post_completion_defect": False,
            "completion_state": "completed",
        }
    )
    module.append_record(records_path, record)
    loaded = module.load_records(records_path)
    assert len(loaded) == 1
    assert loaded[0].task_id == "R-1"


def test_append_record_rejects_duplicate_task_id(tmp_path: Path) -> None:
    module = load_module()
    records_path = tmp_path / "records.json"
    record = module.task_record_from_dict(
        {
            "task_id": "R-1",
            "cohort": "drift_informed",
            "steps_to_completion": 5,
            "rework_events": 0,
            "first_pass_success": True,
            "post_completion_defect": False,
            "completion_state": "completed",
        }
    )
    module.append_record(records_path, record)
    with pytest.raises(ValueError, match="already present"):
        module.append_record(records_path, record)


def test_cmd_ingest_session_appends_record(tmp_path: Path) -> None:
    module = load_module()
    session_path = tmp_path / "session.json"
    records_path = tmp_path / "records.json"
    session_path.write_text(
        json.dumps(
            {
                "tool_calls": 9,
                "task_queue": {
                    "total": 2,
                    "completed": 2,
                    "claimed": 2,
                    "failed": 0,
                    "remaining": 0,
                },
                "orchestration_metrics": {"plans_invalidated": 0, "nudge_degrading": 1},
            }
        ),
        encoding="utf-8",
    )

    import argparse

    args = argparse.Namespace(
        session_json=str(session_path),
        task_id="ingest-1",
        cohort="drift_informed",
        post_completion_defect=False,
        records=str(records_path),
    )
    module.cmd_ingest_session(args)
    loaded = module.load_records(records_path)
    assert len(loaded) == 1
    assert loaded[0].task_id == "ingest-1"
    assert loaded[0].steps_to_completion == 9
    assert loaded[0].rework_events == 1
    assert loaded[0].first_pass_success is False


def test_excluded_task_allows_empty_hypothesis() -> None:
    module = load_module()
    entry = module.manifest_entry_from_dict(
        {
            "task_id": "T-excl",
            "cohort": "control",
            "repo": "mick-gsk/drift",
            "task_type": "chore",
            "outcome_hypothesis": "",
            "started_at": "2026-05-01T10:00:00+00:00",
            "include_in_study": False,
            "exclusion_reason": "Cleanup task without outcome hypothesis",
        }
    )
    assert entry.outcome_hypothesis == ""
    assert entry.include_in_study is False
