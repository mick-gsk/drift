#!/usr/bin/env python3
"""Outcome-first validation study runner.

Implements the first executable slice of the concept in
docs/concepts/outcome-first-validation.md:

- a concrete task/record contract for 14-day studies
- aggregation of the four core metrics per cohort
- deterministic Go/No-Go evaluation against concept thresholds

This slice is intentionally standalone. It does not yet instrument sessions
or populate records automatically; it validates and aggregates study data.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work_artifacts" / "outcome_first_validation"
MANIFEST_FILE = WORK_DIR / "manifest.json"
RECORDS_FILE = WORK_DIR / "records.json"
REPORT_FILE = WORK_DIR / "report.json"

SCHEMA_VERSION = "1.0"

Cohort = Literal["drift_informed", "control"]
CompletionState = Literal["completed", "failed", "abandoned"]


@dataclass(frozen=True)
class TaskManifestEntry:
    """One eligible study task for the 14-day outcome-first protocol."""

    task_id: str
    cohort: Cohort
    repo: str
    task_type: str
    outcome_hypothesis: str
    started_at: str
    completed_at: str | None = None
    completion_state: CompletionState = "completed"
    include_in_study: bool = True
    exclusion_reason: str | None = None


@dataclass(frozen=True)
class TaskRecord:
    """Measured outcome record for one executed study task."""

    task_id: str
    cohort: Cohort
    steps_to_completion: int
    rework_events: int
    first_pass_success: bool
    post_completion_defect: bool
    completion_state: CompletionState
    completed_at: str | None = None


@dataclass(frozen=True)
class CohortMetrics:
    """Aggregated study metrics for a cohort."""

    cohort: Cohort
    sample_size: int
    median_steps_to_completion: float
    rework_rate: float
    first_pass_success_rate: float
    post_completion_defect_rate: float


def _parse_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_iso8601(value: str | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be valid ISO-8601: {value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _require_mapping(raw: Any, path: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be an object")
    return raw


def _require_list(raw: Any, path: str) -> list[Any]:
    if not isinstance(raw, list):
        raise ValueError(f"{path} must be a list")
    return raw


def _require_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _require_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _require_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _validate_cohort(value: str, field_name: str) -> Cohort:
    if value == "drift_informed":
        return "drift_informed"
    if value == "control":
        return "control"
    raise ValueError(f"{field_name} must be 'drift_informed' or 'control'")


def _validate_completion_state(value: str, field_name: str) -> CompletionState:
    if value == "completed":
        return "completed"
    if value == "failed":
        return "failed"
    if value == "abandoned":
        return "abandoned"
    raise ValueError(f"{field_name} must be completed, failed, or abandoned")


def manifest_entry_from_dict(raw: dict[str, Any]) -> TaskManifestEntry:
    started_at = _require_str(raw.get("started_at"), "started_at")
    completed_at_raw = raw.get("completed_at")
    if completed_at_raw is not None and not isinstance(completed_at_raw, str):
        raise ValueError("completed_at must be a string or null")

    include_in_study = raw.get("include_in_study", True)
    if not isinstance(include_in_study, bool):
        raise ValueError("include_in_study must be a boolean")

    # outcome_hypothesis is required only for tasks included in the study
    raw_hypothesis = raw.get("outcome_hypothesis", "")
    if include_in_study:
        outcome_hypothesis = _require_str(raw_hypothesis, "outcome_hypothesis")
    else:
        if not isinstance(raw_hypothesis, str):
            raise ValueError("outcome_hypothesis must be a string")
        outcome_hypothesis = raw_hypothesis

    entry = TaskManifestEntry(
        task_id=_require_str(raw.get("task_id"), "task_id"),
        cohort=_validate_cohort(_require_str(raw.get("cohort"), "cohort"), "cohort"),
        repo=_require_str(raw.get("repo"), "repo"),
        task_type=_require_str(raw.get("task_type"), "task_type"),
        outcome_hypothesis=outcome_hypothesis,
        started_at=started_at,
        completed_at=completed_at_raw,
        completion_state=_validate_completion_state(
            _require_str(raw.get("completion_state", "completed"), "completion_state"),
            "completion_state",
        ),
        include_in_study=include_in_study,
        exclusion_reason=raw.get("exclusion_reason"),
    )

    if entry.exclusion_reason is not None and not isinstance(entry.exclusion_reason, str):
        raise ValueError("exclusion_reason must be a string or null")

    _parse_iso8601(entry.started_at, "started_at")
    completed_dt = _parse_iso8601(entry.completed_at, "completed_at")
    started_dt = _parse_iso8601(entry.started_at, "started_at")
    if started_dt and completed_dt and completed_dt < started_dt:
        raise ValueError("completed_at must not be before started_at")
    if not entry.include_in_study and not entry.exclusion_reason:
        raise ValueError("exclusion_reason is required when include_in_study is false")
    return entry


def task_record_from_dict(raw: dict[str, Any]) -> TaskRecord:
    record = TaskRecord(
        task_id=_require_str(raw.get("task_id"), "task_id"),
        cohort=_validate_cohort(_require_str(raw.get("cohort"), "cohort"), "cohort"),
        steps_to_completion=_require_int(raw.get("steps_to_completion"), "steps_to_completion"),
        rework_events=_require_int(raw.get("rework_events"), "rework_events"),
        first_pass_success=_require_bool(raw.get("first_pass_success"), "first_pass_success"),
        post_completion_defect=_require_bool(
            raw.get("post_completion_defect"), "post_completion_defect"
        ),
        completion_state=_validate_completion_state(
            _require_str(raw.get("completion_state"), "completion_state"),
            "completion_state",
        ),
        completed_at=raw.get("completed_at"),
    )
    if record.steps_to_completion < 1:
        raise ValueError("steps_to_completion must be >= 1")
    if record.rework_events < 0:
        raise ValueError("rework_events must be >= 0")
    if record.completed_at is not None and not isinstance(record.completed_at, str):
        raise ValueError("completed_at must be a string or null")
    _parse_iso8601(record.completed_at, "completed_at")
    return record


def load_manifest(path: Path) -> list[TaskManifestEntry]:
    raw = _require_mapping(_parse_json(path), path.as_posix())
    entries = _require_list(raw.get("tasks"), "tasks")
    parsed = [manifest_entry_from_dict(_require_mapping(entry, "tasks[]")) for entry in entries]
    task_ids = [entry.task_id for entry in parsed]
    if len(task_ids) != len(set(task_ids)):
        raise ValueError("manifest task_id values must be unique")
    return parsed


def load_records(path: Path) -> list[TaskRecord]:
    raw = _require_mapping(_parse_json(path), path.as_posix())
    entries = _require_list(raw.get("records"), "records")
    return [task_record_from_dict(_require_mapping(entry, "records[]")) for entry in entries]


def validate_manifest_records(
    manifest: Sequence[TaskManifestEntry], records: Sequence[TaskRecord]
) -> None:
    manifest_ids = {entry.task_id: entry for entry in manifest if entry.include_in_study}
    seen_record_ids: set[str] = set()
    for record in records:
        if record.task_id not in manifest_ids:
            raise ValueError(f"record task_id not present in included manifest: {record.task_id}")
        manifest_entry = manifest_ids[record.task_id]
        if record.cohort != manifest_entry.cohort:
            raise ValueError(f"record cohort mismatch for {record.task_id}")
        if record.task_id in seen_record_ids:
            raise ValueError(f"duplicate record for task_id: {record.task_id}")
        seen_record_ids.add(record.task_id)


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_cohort_metrics(records: Sequence[TaskRecord]) -> dict[Cohort, CohortMetrics]:
    grouped: dict[Cohort, list[TaskRecord]] = {"drift_informed": [], "control": []}
    for record in records:
        if record.completion_state != "completed":
            continue
        grouped[record.cohort].append(record)

    metrics: dict[Cohort, CohortMetrics] = {}
    for cohort, cohort_records in grouped.items():
        sample_size = len(cohort_records)
        steps = [record.steps_to_completion for record in cohort_records]
        metrics[cohort] = CohortMetrics(
            cohort=cohort,
            sample_size=sample_size,
            median_steps_to_completion=float(statistics.median(steps)) if steps else 0.0,
            rework_rate=_ratio(
                sum(1 for record in cohort_records if record.rework_events > 0), sample_size
            ),
            first_pass_success_rate=_ratio(
                sum(1 for record in cohort_records if record.first_pass_success), sample_size
            ),
            post_completion_defect_rate=_ratio(
                sum(1 for record in cohort_records if record.post_completion_defect), sample_size
            ),
        )
    return metrics


def evaluate_go_no_go(metrics: dict[Cohort, CohortMetrics]) -> dict[str, Any]:
    control = metrics["control"]
    treatment = metrics["drift_informed"]

    steps_improvement = 0.0
    if control.median_steps_to_completion > 0:
        steps_improvement = (
            control.median_steps_to_completion - treatment.median_steps_to_completion
        ) / control.median_steps_to_completion

    rework_improvement = 0.0
    if control.rework_rate > 0:
        rework_improvement = (control.rework_rate - treatment.rework_rate) / control.rework_rate

    first_pass_delta = treatment.first_pass_success_rate - control.first_pass_success_rate
    defect_delta = treatment.post_completion_defect_rate - control.post_completion_defect_rate

    passes = {
        "steps": steps_improvement >= 0.25,
        "rework": rework_improvement >= 0.30,
        "first_pass": first_pass_delta >= 0.15,
        "defects_not_worse": defect_delta <= 0.0,
    }
    improved_count = sum(1 for key in ("steps", "rework", "first_pass") if passes[key])
    decision = "go" if improved_count >= 2 and passes["defects_not_worse"] else "no_go"

    return {
        "decision": decision,
        "passes": passes,
        "improved_metric_count": improved_count,
        "thresholds": {
            "steps": 0.25,
            "rework": 0.30,
            "first_pass": 0.15,
            "defects_not_worse": 0.0,
        },
        "deltas": {
            "steps_improvement": round(steps_improvement, 4),
            "rework_improvement": round(rework_improvement, 4),
            "first_pass_delta": round(first_pass_delta, 4),
            "defect_delta": round(defect_delta, 4),
        },
    }


def build_report(
    manifest: Sequence[TaskManifestEntry], records: Sequence[TaskRecord]
) -> dict[str, Any]:
    validate_manifest_records(manifest, records)
    included_tasks = [entry for entry in manifest if entry.include_in_study]
    metrics = compute_cohort_metrics(records)
    verdict = evaluate_go_no_go(metrics)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "study": {
            "duration_days": 14,
            "included_task_count": len(included_tasks),
            "record_count": len(records),
        },
        "cohort_metrics": {
            cohort: asdict(metric) for cohort, metric in metrics.items()
        },
        "verdict": verdict,
    }


def session_summary_to_task_record(
    summary: dict[str, Any],
    *,
    task_id: str,
    cohort: Cohort,
    post_completion_defect: bool = False,
) -> TaskRecord:
    """Convert a ``DriftSession.summary()`` dict to a ``TaskRecord``.

    Maps:
    - ``tool_calls``                → ``steps_to_completion`` (min 1)
    - ``orchestration_metrics.plans_invalidated``
      + ``orchestration_metrics.nudge_degrading`` → ``rework_events``
    - ``rework_events == 0``        → ``first_pass_success``
    - task_queue.completed > 0      → completion_state "completed"

    ``post_completion_defect`` cannot be auto-derived; callers must supply it.
    """
    tool_calls: int = max(1, int(summary.get("tool_calls", 1)))
    orch: dict[str, Any] = summary.get("orchestration_metrics") or {}
    rework_events: int = int(orch.get("plans_invalidated", 0)) + int(
        orch.get("nudge_degrading", 0)
    )
    first_pass_success: bool = rework_events == 0
    task_queue: dict[str, Any] = summary.get("task_queue") or {}
    completed_count: int = int(task_queue.get("completed", 0))
    failed_count: int = int(task_queue.get("failed", 0))
    if completed_count > 0:
        state: CompletionState = "completed"
    elif failed_count > 0:
        state = "failed"
    else:
        state = "abandoned"
    return TaskRecord(
        task_id=task_id,
        cohort=cohort,
        steps_to_completion=tool_calls,
        rework_events=rework_events,
        first_pass_success=first_pass_success,
        post_completion_defect=post_completion_defect,
        completion_state=state,
    )


def append_record(records_path: Path, record: TaskRecord) -> None:
    """Append a ``TaskRecord`` to the records file (creates if missing)."""
    records_path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_records(records_path) if records_path.exists() else []
    existing_ids = {r.task_id for r in existing}
    if record.task_id in existing_ids:
        raise ValueError(f"task_id already present in records: {record.task_id}")
    all_records = [*existing, record]
    payload = {"records": [asdict(r) for r in all_records]}
    records_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def cmd_validate(args: argparse.Namespace) -> None:
    manifest = load_manifest(Path(args.manifest))
    records = load_records(Path(args.records))
    validate_manifest_records(manifest, records)
    print(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "status": "ok",
                "manifest_tasks": len(manifest),
                "records": len(records),
            },
            indent=2,
        )
    )


def cmd_report(args: argparse.Namespace) -> None:
    manifest = load_manifest(Path(args.manifest))
    records = load_records(Path(args.records))
    report = build_report(manifest, records)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


def cmd_ingest_session(args: argparse.Namespace) -> None:
    session_json = _parse_json(Path(args.session_json))
    record = session_summary_to_task_record(
        session_json,
        task_id=args.task_id,
        cohort=args.cohort,
        post_completion_defect=args.post_completion_defect,
    )
    append_record(Path(args.records), record)
    print(json.dumps({"status": "ok", "appended": asdict(record)}, indent=2))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Outcome-first validation study runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate manifest and records")
    validate_parser.add_argument("--manifest", default=str(MANIFEST_FILE))
    validate_parser.add_argument("--records", default=str(RECORDS_FILE))

    report_parser = subparsers.add_parser("report", help="Build aggregated report")
    report_parser.add_argument("--manifest", default=str(MANIFEST_FILE))
    report_parser.add_argument("--records", default=str(RECORDS_FILE))
    report_parser.add_argument("--output", default=str(REPORT_FILE))

    ingest_parser = subparsers.add_parser(
        "ingest-session", help="Derive a TaskRecord from a DriftSession summary JSON and append it"
    )
    ingest_parser.add_argument("--session-json", required=True, help="Path to session summary JSON")
    ingest_parser.add_argument("--task-id", required=True, help="task_id for the new record")
    ingest_parser.add_argument(
        "--cohort",
        required=True,
        choices=["drift_informed", "control"],
        help="Cohort for the new record",
    )
    ingest_parser.add_argument(
        "--post-completion-defect",
        action="store_true",
        default=False,
        help="Flag this task as having a post-completion defect",
    )
    ingest_parser.add_argument("--records", default=str(RECORDS_FILE))

    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "validate":
        cmd_validate(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "ingest-session":
        cmd_ingest_session(args)
    else:
        raise AssertionError(f"Unhandled command: {args.command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
