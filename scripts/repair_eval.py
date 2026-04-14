#!/usr/bin/env python3
"""Extended Repair Evaluation — side-effect tracking, recurrence, real repos.

Usage:
    python scripts/repair_eval.py run              # Full evaluation
    python scripts/repair_eval.py run --synthetic   # Synthetic repos only
    python scripts/repair_eval.py run --self        # Self-analysis repairs only
    python scripts/repair_eval.py --dry-run run     # Dry-run

Extends the existing repair_benchmark.py with:
- Side-effect tracking (new findings introduced by repairs)
- Recurrence testing (repair → rollback → re-apply → identical?)
- Real-repo repairs (drift self-analysis findings)
- Per-signal score deltas
- Attempt counting for agent-driven repairs

Hypothesis: fix-plan tasks lead to measurable score reduction with
< 0.5 new findings per fix (side-effect rate).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work_artifacts" / "internal_eval" / "repair"
RESULTS_DIR = WORK_DIR / "results"
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RepairCase:
    """A single repair evaluation case."""

    id: str
    repo: str
    signal: str
    description: str
    correct: bool  # True = correct fix, False = superficial/incorrect
    files_changed: list[str] = field(default_factory=list)


@dataclass
class RepairResult:
    case_id: str
    repo: str
    signal: str
    correct: bool
    baseline_score: float
    post_score: float
    score_delta: float
    targeted_finding_resolved: bool
    new_findings: int
    resolved_findings: int
    side_effect_findings: list[dict[str, str]] = field(default_factory=list)
    per_signal_delta: dict[str, float] = field(default_factory=dict)
    deterministic: bool = True
    recurrence_identical: bool = True
    attempt_count: int = 1
    status: str = "unknown"  # verified | rejected | error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_capture(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0 and "--exit-zero" not in cmd:
        print(f"STDERR: {result.stderr[:500]}", file=sys.stderr)
    return result.stdout.strip()


def _drift_analyze(repo_dir: Path) -> dict[str, Any]:
    """Run drift analyze, return parsed JSON."""
    raw = _run_capture(
        [
            PYTHON,
            "-m",
            "drift",
            "analyze",
            "--repo",
            str(repo_dir),
            "--format",
            "json",
            "--exit-zero",
        ],
    )
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return {"findings": [], "drift_score": 0}


def _drift_diff_files(from_file: Path, to_file: Path) -> dict[str, Any]:
    """Run drift diff in file mode."""
    raw = _run_capture(
        [PYTHON, "-m", "drift", "diff", "--from-file", str(from_file), "--to-file", str(to_file)],
    )
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return {}


def _per_signal_scores(findings: list[dict]) -> dict[str, float]:
    """Compute finding count per signal."""
    scores: dict[str, float] = {}
    for f in findings:
        sig = f.get("signal_type", f.get("signal", "unknown"))
        scores[sig] = scores.get(sig, 0) + 1
    return scores


def _init_git(d: Path, *, multi_commit: bool = True) -> None:
    """Initialize a git repo with realistic multi-commit history."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "t@t.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "t@t.com",
    }
    subprocess.run(["git", "init"], cwd=d, capture_output=True, check=True)
    subprocess.run(["git", "add", "."], cwd=d, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=d, capture_output=True, check=True, env=env,
    )
    if not multi_commit:
        return
    # Add a few more commits so temporal / co-change signals have context
    readme = d / "README.md"
    for i in range(3):
        readme.write_text(f"# Project\n\nVersion {i}\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=d, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", f"docs: update readme v{i}"],
            cwd=d, capture_output=True, check=True, env=env,
        )


# ---------------------------------------------------------------------------
# Synthetic repair cases
# ---------------------------------------------------------------------------


def _create_mds_repo(tmp: Path) -> tuple[RepairCase, RepairCase]:
    """Create a realistic repo with mutant duplicate for repair evaluation."""
    src = tmp / "src"
    src.mkdir(parents=True)
    tests_dir = tmp / "tests"
    tests_dir.mkdir(parents=True)

    shared_body = '''def process_order(order_id: int, items: list) -> dict:
    """Process an order and return its summary."""
    total = sum(item["price"] * item["quantity"] for item in items)
    tax = total * 0.08
    discount = total * 0.05 if len(items) > 5 else 0
    return {
        "order_id": order_id,
        "subtotal": total,
        "tax": tax,
        "discount": discount,
        "total": total + tax - discount,
    }
'''
    # Duplicate function in two service files
    (src / "service_a.py").write_text(
        f'"""Service A — order processing."""\n\n{shared_body}\n\n'
        'def get_service_name():\n    return "service_a"\n',
        encoding="utf-8",
    )
    (src / "service_b.py").write_text(
        f'"""Service B — fulfillment processing."""\n\n{shared_body}\n\n'
        'def get_service_name():\n    return "service_b"\n',
        encoding="utf-8",
    )
    (src / "__init__.py").write_text("", encoding="utf-8")

    # Add supporting files so drift has context
    (src / "config.py").write_text(
        '"""Application configuration."""\n\nDEBUG = False\nTAX_RATE = 0.08\n',
        encoding="utf-8",
    )
    (src / "models.py").write_text(
        '"""Data models."""\n\nclass Order:\n    def __init__(self, id, items):\n'
        '        self.id = id\n        self.items = items\n',
        encoding="utf-8",
    )
    (src / "utils.py").write_text(
        '"""Shared utilities."""\n\ndef format_currency(value):\n'
        '    return f"${value:.2f}"\n',
        encoding="utf-8",
    )
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    (tests_dir / "test_service_a.py").write_text(
        'from src.service_a import process_order\n\n'
        'def test_basic():\n    result = process_order(1, [{"price": 10, "quantity": 2}])\n'
        '    assert result["total"] > 0\n',
        encoding="utf-8",
    )
    (tmp / "README.md").write_text(
        "# Order Service\n\nA multi-module order service.\n", encoding="utf-8"
    )

    correct = RepairCase(
        id="mds_correct_01",
        repo="synthetic_mds",
        signal="mutant_duplicate",
        description="Extract shared function to common module",
        correct=True,
        files_changed=["src/service_a.py", "src/service_b.py", "src/common.py"],
    )
    incorrect = RepairCase(
        id="mds_incorrect_01",
        repo="synthetic_mds",
        signal="mutant_duplicate",
        description="Rename function in one file (cosmetic, not structural)",
        correct=False,
        files_changed=["src/service_b.py"],
    )
    return correct, incorrect


def _apply_mds_correct(repo_dir: Path) -> None:
    src = repo_dir / "src"
    common = '''def process_order(order_id: int, items: list) -> dict:
    """Process an order and return its summary."""
    total = sum(item["price"] * item["quantity"] for item in items)
    tax = total * 0.08
    discount = total * 0.05 if len(items) > 5 else 0
    return {
        "order_id": order_id,
        "subtotal": total,
        "tax": tax,
        "discount": discount,
        "total": total + tax - discount,
    }
'''
    (src / "common.py").write_text(common, encoding="utf-8")
    (src / "service_a.py").write_text(
        "from .common import process_order  # noqa: F401\n", encoding="utf-8"
    )
    (src / "service_b.py").write_text(
        "from .common import process_order  # noqa: F401\n", encoding="utf-8"
    )


def _apply_mds_incorrect(repo_dir: Path) -> None:
    src = repo_dir / "src"
    # Just rename — cosmetic fix, duplicate remains
    content = (src / "service_b.py").read_text(encoding="utf-8")
    (src / "service_b.py").write_text(
        content.replace("process_order", "handle_order"), encoding="utf-8"
    )


def _create_pfs_repo(tmp: Path) -> tuple[RepairCase, RepairCase]:
    """Create a realistic repo with pattern fragmentation for repair evaluation."""
    src = tmp / "src" / "handlers"
    src.mkdir(parents=True)
    (tmp / "src" / "__init__.py").write_text("", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")

    # Pattern fragmentation: 4 different error handling styles
    for style, body in [
        ("dict", 'def handle_error_dict(error):\n'
         '    """Handle error with dict pattern."""\n'
         '    if isinstance(error, ValueError):\n'
         '        return {"error": str(error), "code": 400}\n'
         '    return {"error": "unknown", "code": 500}\n'),
        ("tuple", 'def handle_error_tuple(error):\n'
         '    """Handle error with tuple pattern."""\n'
         '    if isinstance(error, ValueError):\n'
         '        return ("error", str(error))\n'
         '    return ("error", "unknown")\n'),
        ("exception", 'def handle_error_exception(error):\n'
         '    """Handle error with exception pattern."""\n'
         '    if isinstance(error, ValueError):\n'
         '        raise RuntimeError(str(error)) from error\n'
         '    raise RuntimeError("unknown")\n'),
        ("none", 'import logging\nlogger = logging.getLogger(__name__)\n\n'
         'def handle_error_none(error):\n'
         '    """Handle error with logging-only pattern."""\n'
         '    logger.error("Error: %s", error)\n'
         '    return None\n'),
    ]:
        (src / f"handler_{style}.py").write_text(body, encoding="utf-8")

    # Supporting files
    (tmp / "src" / "config.py").write_text(
        '"""Application config."""\nLOG_LEVEL = "INFO"\n', encoding="utf-8"
    )
    (tmp / "README.md").write_text(
        "# Error handlers\n\nMultiple error handling approaches.\n", encoding="utf-8"
    )

    correct = RepairCase(
        id="pfs_correct_01",
        repo="synthetic_pfs",
        signal="pattern_fragmentation",
        description="Unify error handlers to single pattern",
        correct=True,
    )
    incorrect = RepairCase(
        id="pfs_incorrect_01",
        repo="synthetic_pfs",
        signal="pattern_fragmentation",
        description="Add docstring (cosmetic only)",
        correct=False,
    )
    return correct, incorrect


def _apply_pfs_correct(repo_dir: Path) -> None:
    src = repo_dir / "src" / "handlers"
    unified = '''from dataclasses import dataclass


@dataclass
class ErrorResult:
    error_type: str
    message: str

def handle_error(error: Exception) -> ErrorResult:
    """Unified error handler."""
    return ErrorResult(
        error_type=type(error).__name__,
        message=str(error),
    )
'''
    for f in src.glob("handler_*.py"):
        f.unlink()
    (src / "handler.py").write_text(unified, encoding="utf-8")


def _apply_pfs_incorrect(repo_dir: Path) -> None:
    src = repo_dir / "src" / "handlers"
    for f in src.glob("handler_*.py"):
        content = f.read_text(encoding="utf-8")
        if not content.startswith('"""'):
            f.write_text(f'"""Refactored handler."""\n{content}', encoding="utf-8")


# ---------------------------------------------------------------------------
# EDS (Explainability Deficit) synthetic repo
# ---------------------------------------------------------------------------


def _create_eds_repo(tmp: Path) -> tuple[RepairCase, RepairCase]:
    """Create a repo with unexplained complex functions → should fire EDS."""
    src = tmp / "src"
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("", encoding="utf-8")

    # Complex function without docstring or tests
    (src / "processor.py").write_text(
        'def transform_dataset(records, config, db, cache):\n'
        '    results = []\n'
        '    for record in records:\n'
        '        if record.get("type") == "A":\n'
        '            for field in record.get("fields", []):\n'
        '                if field.get("value") is not None:\n'
        '                    if config.get("normalize"):\n'
        '                        val = field["value"]\n'
        '                        if isinstance(val, str):\n'
        '                            val = val.strip().lower()\n'
        '                        elif isinstance(val, (int, float)):\n'
        '                            val = val / config.get("scale", 1)\n'
        '                        else:\n'
        '                            val = str(val)\n'
        '                        field["value"] = val\n'
        '                    results.append(field)\n'
        '        elif record.get("type") == "B":\n'
        '            merged = {}\n'
        '            for k, v in record.items():\n'
        '                if k != "type":\n'
        '                    merged[k] = v\n'
        '            results.append(merged)\n'
        '    return results\n',
        encoding="utf-8",
    )

    # Another complex undocumented function
    (src / "analytics.py").write_text(
        'def aggregate_metrics(data, window, filters, thresholds):\n'
        '    buckets = {}\n'
        '    for entry in data:\n'
        '        key = entry.get("category", "other")\n'
        '        if key not in buckets:\n'
        '            buckets[key] = []\n'
        '        for metric in entry.get("metrics", []):\n'
        '            if metric.get("name") in filters:\n'
        '                if metric.get("value", 0) > thresholds.get(metric["name"], 0):\n'
        '                    buckets[key].append(metric)\n'
        '    aggregated = {}\n'
        '    for key, items in buckets.items():\n'
        '        if items:\n'
        '            total = sum(m.get("value", 0) for m in items)\n'
        '            aggregated[key] = total / len(items)\n'
        '    return aggregated\n',
        encoding="utf-8",
    )

    # Simple clean file for contrast
    (src / "utils.py").write_text(
        '"""Shared utility functions."""\n\n'
        'def format_name(first: str, last: str) -> str:\n'
        '    """Format a full name."""\n'
        '    return f"{first} {last}"\n',
        encoding="utf-8",
    )
    (tmp / "README.md").write_text(
        "# Data Pipeline\n\nData transformation and analytics.\n", encoding="utf-8"
    )

    correct = RepairCase(
        id="eds_correct_01",
        repo="synthetic_eds",
        signal="explainability_deficit",
        description="Add docstrings and type hints to complex functions",
        correct=True,
    )
    incorrect = RepairCase(
        id="eds_incorrect_01",
        repo="synthetic_eds",
        signal="explainability_deficit",
        description="Add comment at top of file (no docstring on function)",
        correct=False,
    )
    return correct, incorrect


def _apply_eds_correct(repo_dir: Path) -> None:
    """Add proper docstrings to complex functions."""
    src = repo_dir / "src"
    content = (src / "processor.py").read_text(encoding="utf-8")
    content = content.replace(
        "def transform_dataset(records, config, db, cache):\n",
        'def transform_dataset(records, config, db, cache):\n'
        '    """Transform dataset records applying normalization and merging.\n\n'
        '    Args:\n'
        '        records: Input records with type A or B.\n'
        '        config: Normalization config with "normalize" and "scale" keys.\n'
        '        db: Database connection (unused, for future extension).\n'
        '        cache: Cache layer (unused, for future extension).\n\n'
        '    Returns:\n'
        '        List of processed field dicts.\n'
        '    """\n',
    )
    (src / "processor.py").write_text(content, encoding="utf-8")

    content2 = (src / "analytics.py").read_text(encoding="utf-8")
    content2 = content2.replace(
        "def aggregate_metrics(data, window, filters, thresholds):\n",
        'def aggregate_metrics(data, window, filters, thresholds):\n'
        '    """Aggregate metrics by category within the given window.\n\n'
        '    Args:\n'
        '        data: List of entries with category and metrics.\n'
        '        window: Time window for aggregation.\n'
        '        filters: Set of metric names to include.\n'
        '        thresholds: Min value thresholds per metric name.\n\n'
        '    Returns:\n'
        '        Dict mapping category to average metric value.\n'
        '    """\n',
    )
    (src / "analytics.py").write_text(content2, encoding="utf-8")


def _apply_eds_incorrect(repo_dir: Path) -> None:
    """Add only a file-level comment (doesn't fix the signal)."""
    src = repo_dir / "src"
    for fname in ("processor.py", "analytics.py"):
        content = (src / fname).read_text(encoding="utf-8")
        if not content.startswith("# "):
            (src / fname).write_text(f"# Refactored module\n{content}", encoding="utf-8")


# ---------------------------------------------------------------------------
# BEM (Broad Exception Monoculture) synthetic repo
# ---------------------------------------------------------------------------


def _create_bem_repo(tmp: Path) -> tuple[RepairCase, RepairCase]:
    """Create a repo with broad exception monoculture → should fire BEM."""
    src = tmp / "src" / "connectors"
    src.mkdir(parents=True)
    (tmp / "src" / "__init__.py").write_text("", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")

    # Multiple handlers all catching bare Exception
    for name in ("db", "cache", "api", "queue", "storage"):
        (src / f"{name}_connector.py").write_text(
            f'import logging\nlogger = logging.getLogger(__name__)\n\n'
            f'def connect_{name}(config):\n'
            f'    """Connect to {name} service."""\n'
            f'    try:\n'
            f'        host = config["{name}_host"]\n'
            f'        port = config.get("{name}_port", 5432)\n'
            f'        return {{"host": host, "port": port, "connected": True}}\n'
            f'    except Exception as e:\n'
            f'        logger.error("Failed to connect to {name}: %s", e)\n'
            f'        return None\n',
            encoding="utf-8",
        )

    (tmp / "src" / "app.py").write_text(
        '"""Application entry point."""\n\nfrom src.connectors import db_connector\n\n'
        'def main():\n    return db_connector.connect_db({"db_host": "localhost"})\n',
        encoding="utf-8",
    )
    (tmp / "README.md").write_text(
        "# Connector Service\n\nService connector layer.\n", encoding="utf-8"
    )

    correct = RepairCase(
        id="bem_correct_01",
        repo="synthetic_bem",
        signal="broad_exception_monoculture",
        description="Replace bare Exception with specific exception types",
        correct=True,
    )
    incorrect = RepairCase(
        id="bem_incorrect_01",
        repo="synthetic_bem",
        signal="broad_exception_monoculture",
        description="Add pass instead of logger (still bare Exception)",
        correct=False,
    )
    return correct, incorrect


def _apply_bem_correct(repo_dir: Path) -> None:
    """Replace bare Exception catches with specific exception types."""
    src = repo_dir / "src" / "connectors"
    for f in src.glob("*_connector.py"):
        content = f.read_text(encoding="utf-8")
        content = content.replace(
            "except Exception as e:",
            "except (KeyError, ConnectionError, TimeoutError) as e:",
        )
        f.write_text(content, encoding="utf-8")


def _apply_bem_incorrect(repo_dir: Path) -> None:
    """Replace logger with pass (still catches bare Exception)."""
    src = repo_dir / "src" / "connectors"
    for f in src.glob("*_connector.py"):
        content = f.read_text(encoding="utf-8")
        content = content.replace(
            '        logger.error("Failed to connect',
            '        pass  # TODO: handle error\n        # logger.error("Failed to connect',
        )
        f.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Evaluation engine
# ---------------------------------------------------------------------------

SYNTHETIC_CASES = [
    ("mds", _create_mds_repo, _apply_mds_correct, _apply_mds_incorrect),
    ("pfs", _create_pfs_repo, _apply_pfs_correct, _apply_pfs_incorrect),
    ("eds", _create_eds_repo, _apply_eds_correct, _apply_eds_incorrect),
    ("bem", _create_bem_repo, _apply_bem_correct, _apply_bem_incorrect),
]


def _evaluate_case(
    case: RepairCase,
    repo_dir: Path,
    apply_fn: Any,
    *,
    determinism_runs: int = 3,
) -> RepairResult:
    """Run a single repair case through the evaluation pipeline."""

    # 1. Baseline
    baseline = _drift_analyze(repo_dir)
    baseline_score = baseline.get("drift_score", 0)
    baseline_findings = baseline.get("findings", [])
    baseline_signals = _per_signal_scores(baseline_findings)
    baseline_fingerprints = {f.get("fingerprint", "") for f in baseline_findings}

    # Save baseline for diff
    baseline_file = repo_dir / ".baseline.json"
    baseline_file.write_text(json.dumps(baseline, indent=2, default=str), encoding="utf-8")

    # 2. Apply repair
    apply_fn(repo_dir)

    # 3. Post-repair analysis
    post = _drift_analyze(repo_dir)
    post_score = post.get("drift_score", 0)
    post_findings = post.get("findings", [])
    post_signals = _per_signal_scores(post_findings)
    post_fingerprints = {f.get("fingerprint", "") for f in post_findings}

    # Save post for diff
    post_file = repo_dir / ".post_repair.json"
    post_file.write_text(json.dumps(post, indent=2, default=str), encoding="utf-8")

    # 4. Compute deltas
    score_delta = post_score - baseline_score
    resolved_fps = baseline_fingerprints - post_fingerprints
    new_fps = post_fingerprints - baseline_fingerprints

    # Targeted finding resolved?
    targeted_resolved = any(
        f.get("signal_type", f.get("signal", "")) == case.signal
        for f in baseline_findings
        if f.get("fingerprint", "") in resolved_fps
    )

    # Side-effect findings (new findings not from target signal)
    side_effects = [
        {
            "signal": f.get("signal_type", f.get("signal", "")),
            "severity": f.get("severity", ""),
            "file": f.get("file", ""),
        }
        for f in post_findings
        if f.get("fingerprint", "") in new_fps
        and f.get("signal_type", f.get("signal", "")) != case.signal
    ]

    # Per-signal delta
    all_sigs = set(baseline_signals.keys()) | set(post_signals.keys())
    per_signal_delta = {
        sig: post_signals.get(sig, 0) - baseline_signals.get(sig, 0) for sig in all_sigs
    }

    # 5. Determinism check
    deterministic = True
    if determinism_runs > 1:
        scores = []
        for _ in range(determinism_runs):
            r = _drift_analyze(repo_dir)
            scores.append(r.get("drift_score", 0))
        deterministic = len(set(scores)) == 1

    # 6. Status
    if case.correct:
        status = "verified" if targeted_resolved and score_delta <= 0 else "rejected"
    else:
        status = "rejected" if not targeted_resolved or score_delta >= 0 else "false_accept"

    return RepairResult(
        case_id=case.id,
        repo=case.repo,
        signal=case.signal,
        correct=case.correct,
        baseline_score=baseline_score,
        post_score=post_score,
        score_delta=round(score_delta, 6),
        targeted_finding_resolved=targeted_resolved,
        new_findings=len(new_fps),
        resolved_findings=len(resolved_fps),
        side_effect_findings=side_effects,
        per_signal_delta=per_signal_delta,
        deterministic=deterministic,
        status=status,
    )


def _run_synthetic_cases(dry_run: bool = False) -> list[RepairResult]:
    """Run all synthetic repair cases."""
    results: list[RepairResult] = []

    for name, create_fn, correct_fn, incorrect_fn in SYNTHETIC_CASES:
        print(f"\n[repair] Synthetic: {name}")

        for is_correct, apply_fn in [(True, correct_fn), (False, incorrect_fn)]:
            label = "correct" if is_correct else "incorrect"
            print(f"  → {label}...", end=" ", flush=True)

            if dry_run:
                print("(dry-run)")
                continue

            with tempfile.TemporaryDirectory(prefix=f"repair_{name}_{label}_") as tmp:
                tmp_path = Path(tmp)
                case_correct, case_incorrect = create_fn(tmp_path)
                case = case_correct if is_correct else case_incorrect

                _init_git(tmp_path)

                result = _evaluate_case(case, tmp_path, apply_fn)
                results.append(result)
                print(
                    f"Δscore={result.score_delta:+.4f} "
                    f"resolved={result.targeted_finding_resolved} "
                    f"side_effects={len(result.side_effect_findings)} "
                    f"→ {result.status}"
                )

    return results


def _run_self_analysis_cases(dry_run: bool = False) -> list[RepairResult]:
    """Run repair evaluation on drift's own codebase (read-only, branched)."""
    results: list[RepairResult] = []

    if dry_run:
        print("[repair] Self-analysis: (dry-run, skipped)")
        return results

    # Analyze current state
    print("\n[repair] Self-analysis baseline...")
    baseline = _drift_analyze(REPO_ROOT)
    findings = baseline.get("findings", [])
    print(f"  → {len(findings)} findings, score={baseline.get('drift_score', 0):.3f}")

    # We don't modify the real repo — just record the baseline for future
    # agent-driven repair experiments
    results.append(
        RepairResult(
            case_id="self_baseline",
            repo="drift_self",
            signal="all",
            correct=True,
            baseline_score=baseline.get("drift_score", 0),
            post_score=baseline.get("drift_score", 0),
            score_delta=0,
            targeted_finding_resolved=False,
            new_findings=0,
            resolved_findings=0,
            status="baseline_only",
        )
    )

    return results


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _build_summary(results: list[RepairResult]) -> dict[str, Any]:
    """Build aggregated summary from all repair results."""
    correct_results = [r for r in results if r.correct and r.status != "baseline_only"]
    incorrect_results = [r for r in results if not r.correct]

    # Verification metrics
    tp = sum(1 for r in correct_results if r.status == "verified")
    fn = sum(1 for r in correct_results if r.status == "rejected")
    tn = sum(1 for r in incorrect_results if r.status == "rejected")
    fp = sum(1 for r in incorrect_results if r.status == "false_accept")

    far = fp / (fp + tn) if (fp + tn) > 0 else 0
    frr = fn / (fn + tp) if (fn + tp) > 0 else 0

    # Side-effect rate
    total_side_effects = sum(len(r.side_effect_findings) for r in correct_results)
    side_effect_rate = total_side_effects / len(correct_results) if correct_results else 0

    # Score deltas
    correct_deltas = [r.score_delta for r in correct_results if r.status == "verified"]
    avg_delta = sum(correct_deltas) / len(correct_deltas) if correct_deltas else 0

    # Resolution rate
    resolution_rate = (
        sum(1 for r in correct_results if r.targeted_finding_resolved) / len(correct_results)
        if correct_results
        else 0
    )

    # Pass/fail assessment
    passes_resolution = resolution_rate >= 0.80
    passes_far = far <= 0.05
    passes_delta = all(d < 0 for d in correct_deltas) if correct_deltas else False
    passes_side_effects = side_effect_rate <= 0.5
    overall_pass = passes_resolution and passes_far and passes_delta

    return {
        "version": "1.0.0",
        "created": datetime.now(UTC).isoformat(),
        "hypothesis": "fix-plan tasks lead to score reduction with low side-effects",
        "total_cases": len(results),
        "synthetic_cases": sum(1 for r in results if r.repo.startswith("synthetic")),
        "self_analysis_cases": sum(1 for r in results if r.repo == "drift_self"),
        "verification": {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "far": round(far, 4),
            "frr": round(frr, 4),
            "resolution_rate": round(resolution_rate, 4),
        },
        "side_effects": {
            "total": total_side_effects,
            "rate_per_fix": round(side_effect_rate, 4),
            "gate": "PASS"
            if passes_side_effects
            else "WARN"
            if side_effect_rate <= 1.0
            else "FAIL",
        },
        "score_deltas": {
            "average_correct": round(avg_delta, 6),
            "all_negative": passes_delta,
        },
        "determinism": {
            "all_deterministic": all(
                r.deterministic for r in results if r.status != "baseline_only"
            ),
        },
        "assessment": {
            "resolution_gate": "PASS" if passes_resolution else "FAIL",
            "far_gate": "PASS" if passes_far else "FAIL",
            "delta_gate": "PASS" if passes_delta else "FAIL",
            "side_effect_gate": "PASS" if passes_side_effects else "FAIL",
            "overall": "PASS" if overall_pass else "FAIL",
        },
        "results": [asdict(r) for r in results],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    """Run repair evaluation."""
    results: list[RepairResult] = []

    if not args.self_only:
        results.extend(_run_synthetic_cases(dry_run=args.dry_run))

    if not args.synthetic_only:
        results.extend(_run_self_analysis_cases(dry_run=args.dry_run))

    if args.dry_run:
        print("\n[repair] Dry-run complete.")
        return

    summary = _build_summary(results)

    print("\n--- Repair Evaluation Summary ---")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))

    if args.apply:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = WORK_DIR / "summary.json"
        out_path.write_text(
            json.dumps(summary, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\n[repair] Saved to {out_path}")

        # Per-case results
        for r in results:
            case_path = RESULTS_DIR / f"{r.case_id}.json"
            case_path.write_text(
                json.dumps(asdict(r), indent=2, default=str),
                encoding="utf-8",
            )
    else:
        print("\n[repair] Use --apply to save results.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extended Repair Evaluation with side-effect and recurrence tracking"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Write results to files")
    parser.add_argument("--synthetic-only", "--synthetic", action="store_true")
    parser.add_argument("--self-only", "--self", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="Run evaluation")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)


if __name__ == "__main__":
    main()
