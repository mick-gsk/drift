#!/usr/bin/env python3
"""Agentischer A/B-Harness — Controlled evaluation of drift brief effectiveness.

Usage:
    python scripts/ab_harness.py run                    # Full pipeline (mock only)
    python scripts/ab_harness.py run --mode mock        # Deterministic mock agents
    python scripts/ab_harness.py run --mode llm         # LLM-backed agents (needs API key)
    python scripts/ab_harness.py run --dry-run          # No clones, no analysis
    python scripts/ab_harness.py stats                  # Compute stats from outcomes
    python scripts/ab_harness.py report                 # Generate summary report

Wraps brief_ab_study pipeline components with:
- Automated paired outcome comparison
- Statistical tests (Wilcoxon signed-rank, Cohen's d)
- Effect-size classification
- Gate-based pass/fail assessment

Hypothesis: Agent tasks with drift brief produce lower drift scores
than without. Cohen's d ≥ 0.5 on ≥60% of tasks (H4 — agentische Qualität).

Environment:
    OPENAI_API_KEY        Required for --mode llm
    DRIFT_STUDY_MODEL     Override LLM model (default: gpt-4o)
"""

from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_FILE = REPO_ROOT / "benchmarks" / "brief_study_corpus.json"
WORK_DIR = REPO_ROOT / "work_artifacts" / "internal_eval" / "ab_harness"
OUTCOMES_FILE = WORK_DIR / "outcomes.json"
REPORT_FILE = WORK_DIR / "report.json"
PYTHON = sys.executable

# Statistical thresholds
COHENS_D_THRESHOLD = 0.5  # medium effect
ALPHA = 0.05
TASK_PASS_RATE_REQUIRED = 0.60  # 60% of tasks must show effect


def _mock_mode_interpretation(mock_mode: object) -> str:
    if mock_mode == "neutral":
        return "brief_effect_with_structurally_equivalent_edits"
    if mock_mode == "biased":
        return "structural_fixture_bias"
    return "unknown_mock_mode"


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def _wilcoxon_signed_rank(x: list[float], y: list[float]) -> tuple[float, float]:
    """Wilcoxon signed-rank test. Returns (statistic, p_value).

    Uses scipy if available, otherwise returns (0, 1).
    """
    try:
        from scipy.stats import wilcoxon  # noqa: PLC0415

        stat, p = wilcoxon(x, y, alternative="two-sided")
        return (float(stat), float(p))
    except ImportError:
        pass

    # Manual approximation for small samples
    diffs = [a - b for a, b in zip(x, y, strict=False) if a != b]
    n = len(diffs)
    if n < 5:
        return (0.0, 1.0)

    abs_diffs = [(abs(d), d) for d in diffs]
    abs_diffs.sort(key=lambda t: t[0])

    # Assign ranks
    ranks: list[float] = []
    i = 0
    while i < n:
        j = i
        while j < n - 1 and abs_diffs[j + 1][0] == abs_diffs[j][0]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1
        for _ in range(i, j + 1):
            ranks.append(avg_rank)
        i = j + 1

    w_plus = sum(r for r, (_, d) in zip(ranks, abs_diffs, strict=True) if d > 0)
    w_minus = sum(r for r, (_, d) in zip(ranks, abs_diffs, strict=True) if d < 0)
    w = min(w_plus, w_minus)

    # Normal approximation for p-value
    mean_w = n * (n + 1) / 4
    var_w = n * (n + 1) * (2 * n + 1) / 24
    if var_w == 0:
        return (w, 1.0)
    z = (w - mean_w) / math.sqrt(var_w)
    p = 2 * (1 - _norm_cdf(abs(z)))
    return (w, max(0.0, p))


def _cohens_d(x: list[float], y: list[float]) -> float:
    """Compute Cohen's d for paired samples."""
    diffs = [a - b for a, b in zip(x, y, strict=False)]
    n = len(diffs)
    if n < 2:
        return 0.0
    mean_d = sum(diffs) / n
    var_d = sum((d - mean_d) ** 2 for d in diffs) / (n - 1)
    sd_d = math.sqrt(var_d) if var_d > 0 else 1e-10
    return mean_d / sd_d


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _effect_size_label(d: float) -> str:
    d_abs = abs(d)
    if d_abs < 0.2:
        return "negligible"
    if d_abs < 0.5:
        return "small"
    if d_abs < 0.8:
        return "medium"
    return "large"


# ---------------------------------------------------------------------------
# Severity-weighted cost (shared with brief_ab_study)
# ---------------------------------------------------------------------------

_SEVERITY_WEIGHTS = {"critical": 8, "high": 4, "medium": 2, "low": 1, "info": 0}


def _weighted_cost(findings: list[dict]) -> float:
    return sum(_SEVERITY_WEIGHTS.get(str(f.get("severity", "info")).lower(), 0) for f in findings)


# ---------------------------------------------------------------------------
# Mock agent (deterministic, no API key)
# ---------------------------------------------------------------------------


def _mock_agent_edit(
    task: dict[str, Any],
    has_brief: bool,
    rng: random.Random,
    *,
    mock_mode: str = "biased",
) -> str:
    """Produce a mock code edit.

    ``mock_mode="biased"`` (default, original behaviour):
        Treatment arm produces structurally clean code; control arm produces
        deliberately duplicated try/except handlers.  This guarantees a high
        Cohen's d but measures structural bias, not *brief* effectiveness.

    ``mock_mode="neutral"``:
        Both arms produce structurally equivalent single-function edits.
        Only the naming style differs (guideline-compliant vs. generic).
        Use this mode to measure the actual effect of receiving a drift brief.
    """
    target = task["target_files"][0] if task["target_files"] else "file.py"

    if mock_mode == "neutral":
        # Both arms get structurally identical single-function edits; only naming differs.
        name = (
            f"fix_{task['id'].replace('-', '_').lower()}"
            if has_brief
            else f"handler_{rng.randint(1000, 9999)}"
        )
        lines = [
            f"def {name}():",
            f'    """Implements: {task["task_description"][:50]}"""',
            "    pass",
        ]
    elif has_brief:
        lines = [
            "# Refactored per drift brief constraints",
            f"def fix_{task['id'].replace('-', '_').lower()}():",
            f'    """Implements: {task["task_description"][:50]}"""',
            "    pass",
        ]
    else:
        tag = rng.randint(1000, 9999)
        lines = [
            "# Quick fix",
            f"def handler_{tag}():",
            '    """Generated handler."""',
            "    try:",
            "        result = do_something()",
            "    except Exception:",
            "        pass",
            "    return result",
            "",
            f"def handler_{tag + 1}():",
            '    """Similar handler."""',
            "    try:",
            "        result = do_something()",
            "    except Exception:",
            "        pass",
            "    return result",
        ]

    added = "\n".join(f"+{line}" for line in lines)
    return (
        f"diff --git a/{target} b/{target}\n"
        f"--- a/{target}\n+++ b/{target}\n"
        f"@@ -1,0 +1,{len(lines)} @@\n{added}\n"
    )


# ---------------------------------------------------------------------------
# Drift analysis helpers
# ---------------------------------------------------------------------------


def _drift_analyze(repo_dir: Path) -> dict[str, Any]:
    result = subprocess.run(
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
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    raw = result.stdout
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return json.loads(raw[start:end])
    return {"findings": [], "drift_score": 0}


def _shallow_clone(url: str, ref: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, "--single-branch", url, str(dest)],
        check=True,
        capture_output=True,
        timeout=300,
    )


def _apply_mock_edit(repo_dir: Path, diff_text: str) -> None:
    """Apply mock edit by appending additions to target file."""
    lines_to_add: list[str] = []
    target_file = None
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            target_file = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            lines_to_add.append(line[1:])

    if target_file and lines_to_add:
        target = repo_dir / target_file
        if target.exists():
            orig = target.read_text(encoding="utf-8", errors="replace")
            target.write_text(orig + "\n" + "\n".join(lines_to_add) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _load_corpus() -> list[dict[str, Any]]:
    if not CORPUS_FILE.exists():
        sys.exit(f"Corpus not found: {CORPUS_FILE}")
    data = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    return data["tasks"]


def cmd_run(args: argparse.Namespace) -> None:
    """Run paired A/B experiment."""
    if args.mode == "llm":
        # FU-001: fail fast and operatively before any clone/analysis cost.
        sys.exit(
            "[ab] error: --mode llm is not implemented (no LLM adapter wired). "
            "Remediation: re-run with --mode mock to use the deterministic "
            "mock agent, or implement the LLM adapter and remove this guard. "
            "See audit/follow-up.md FU-001."
        )
    tasks = _load_corpus()
    rng = random.Random(42)
    outcomes: list[dict[str, Any]] = []

    print(f"[ab] Running {len(tasks)} tasks × 2 conditions...")

    for task in tasks:
        tid = task["id"]
        print(f"\n[ab] Task: {tid}")

        for condition in ["control", "treatment"]:
            has_brief = condition == "treatment"
            label = "B (brief)" if has_brief else "A (no brief)"

            if args.dry_run:
                print(f"  {label}: dry-run, skipped")
                outcomes.append(
                    {
                        "task_id": tid,
                        "condition": condition,
                        "drift_score": 0,
                        "finding_count": 0,
                        "weighted_cost": 0,
                        "dry_run": True,
                    }
                )
                continue

            with tempfile.TemporaryDirectory(prefix=f"ab_{tid}_{condition}_") as tmpdir:
                repo_dir = Path(tmpdir) / "repo"

                # Clone
                try:
                    _shallow_clone(task["repo_url"], task["ref"], repo_dir)
                except Exception as exc:
                    print(f"  {label}: clone failed: {exc}")
                    continue

                # Generate edit
                if args.mode == "mock":
                    diff = _mock_agent_edit(task, has_brief, rng, mock_mode=args.mock_mode)
                    _apply_mock_edit(repo_dir, diff)
                else:
                    # FU-001: --mode llm has no real adapter yet. Silently
                    # falling back to mock used to mislabel mock data as LLM
                    # data in outcomes.json. Fail operatively instead so
                    # callers see a clear, actionable error.
                    sys.exit(
                        "[ab] error: --mode llm is not implemented "
                        "(no LLM adapter wired). "
                        "Remediation: re-run with --mode mock to use the "
                        "deterministic mock agent, or implement the LLM "
                        "adapter and remove this guard. See "
                        "audit/follow-up.md FU-001."
                    )

                # Measure
                result = _drift_analyze(repo_dir)
                findings = result.get("findings", [])
                score = result.get("drift_score", 0)
                cost = _weighted_cost(findings)

                outcomes.append(
                    {
                        "task_id": tid,
                        "condition": condition,
                        "drift_score": score,
                        "finding_count": len(findings),
                        "weighted_cost": cost,
                        "signals": list(
                            {f.get("signal_type", f.get("signal", "")) for f in findings}
                        ),
                    }
                )
                print(f"  {label}: score={score:.3f} findings={len(findings)} cost={cost:.1f}")

    # Save outcomes
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    OUTCOMES_FILE.write_text(
        json.dumps(
            {
                "outcomes": outcomes,
                "mock_mode": args.mock_mode,
                "created": datetime.now(UTC).isoformat(),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(f"\n[ab] Outcomes saved to {OUTCOMES_FILE}")
    print("[ab] Run 'stats' for statistical analysis.")


def cmd_stats(args: argparse.Namespace) -> None:
    """Compute statistical tests from outcomes."""
    if not OUTCOMES_FILE.exists():
        sys.exit(f"No outcomes file: {OUTCOMES_FILE}. Run 'run' first.")

    data = json.loads(OUTCOMES_FILE.read_text(encoding="utf-8"))
    outcomes = data["outcomes"]

    # Group by task_id
    by_task: dict[str, dict[str, dict]] = {}
    for o in outcomes:
        if o.get("dry_run"):
            continue
        tid = o["task_id"]
        by_task.setdefault(tid, {})[o["condition"]] = o

    # Paired data
    control_scores: list[float] = []
    treatment_scores: list[float] = []
    control_costs: list[float] = []
    treatment_costs: list[float] = []
    task_ids: list[str] = []

    for tid, conds in sorted(by_task.items()):
        if "control" in conds and "treatment" in conds:
            task_ids.append(tid)
            control_scores.append(conds["control"]["drift_score"])
            treatment_scores.append(conds["treatment"]["drift_score"])
            control_costs.append(conds["control"]["weighted_cost"])
            treatment_costs.append(conds["treatment"]["weighted_cost"])

    n = len(task_ids)
    if n < 3:
        print(f"[stats] Insufficient paired data ({n} pairs, need ≥3)")
        return

    # Score analysis
    w_score, p_score = _wilcoxon_signed_rank(control_scores, treatment_scores)
    d_score = _cohens_d(control_scores, treatment_scores)

    # Cost analysis
    w_cost, p_cost = _wilcoxon_signed_rank(control_costs, treatment_costs)
    d_cost = _cohens_d(control_costs, treatment_costs)

    # Per-task effect direction
    tasks_improved = sum(
        1 for cs, ts in zip(control_scores, treatment_scores, strict=True) if ts < cs
    )
    tasks_same = sum(
        1 for cs, ts in zip(control_scores, treatment_scores, strict=True) if ts == cs
    )
    tasks_degraded = sum(
        1 for cs, ts in zip(control_scores, treatment_scores, strict=True) if ts > cs
    )
    improvement_rate = tasks_improved / n if n > 0 else 0

    # Gate assessment
    passes_effect = abs(d_score) >= COHENS_D_THRESHOLD
    passes_significance = p_score < ALPHA
    passes_rate = improvement_rate >= TASK_PASS_RATE_REQUIRED
    overall = passes_effect and passes_significance

    stats = {
        "version": "1.0.0",
        "created": datetime.now(UTC).isoformat(),
        "hypothesis": "H4: drift brief reduces agent-introduced drift",
        "n_pairs": n,
        "score_analysis": {
            "wilcoxon_W": round(w_score, 4),
            "wilcoxon_p": round(p_score, 6),
            "cohens_d": round(d_score, 4),
            "effect_size": _effect_size_label(d_score),
            "mean_control": round(sum(control_scores) / n, 4),
            "mean_treatment": round(sum(treatment_scores) / n, 4),
            "mean_delta": round(
                sum(c - t for c, t in zip(control_scores, treatment_scores, strict=True)) / n,
                4,
            ),
        },
        "cost_analysis": {
            "wilcoxon_W": round(w_cost, 4),
            "wilcoxon_p": round(p_cost, 6),
            "cohens_d": round(d_cost, 4),
            "effect_size": _effect_size_label(d_cost),
        },
        "per_task": {
            "improved": tasks_improved,
            "same": tasks_same,
            "degraded": tasks_degraded,
            "improvement_rate": round(improvement_rate, 4),
        },
        "gates": {
            "effect_size": "PASS" if passes_effect else "FAIL",
            "significance": "PASS" if passes_significance else "FAIL",
            "improvement_rate": "PASS" if passes_rate else "FAIL",
            "overall": "PASS" if overall else "FAIL",
        },
        "thresholds": {
            "cohens_d_min": COHENS_D_THRESHOLD,
            "alpha": ALPHA,
            "task_pass_rate_min": TASK_PASS_RATE_REQUIRED,
        },
    }

    # Print
    print("\n--- A/B Harness Statistical Analysis ---")
    print(json.dumps(stats, indent=2))

    # Save
    stats_path = WORK_DIR / "stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    print(f"\n[stats] Saved to {stats_path}")


def cmd_report(args: argparse.Namespace) -> None:
    """Generate final summary report combining outcomes and stats."""
    if not OUTCOMES_FILE.exists():
        sys.exit("No outcomes. Run 'run' first.")

    stats_path = WORK_DIR / "stats.json"
    if not stats_path.exists():
        sys.exit("No stats. Run 'stats' first.")

    outcomes = json.loads(OUTCOMES_FILE.read_text(encoding="utf-8"))
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    mock_mode = str(outcomes.get("mock_mode", "unknown"))

    report = {
        "version": "1.0.0",
        "created": datetime.now(UTC).isoformat(),
        "building_block": "Baustein 3: Agentischer A/B-Harness",
        "hypothesis": "H4: drift brief reduces agent-introduced drift (Cohen's d ≥ 0.5)",
        "corpus": str(CORPUS_FILE),
        "mock_mode": mock_mode,
        "mock_mode_interpretation": _mock_mode_interpretation(mock_mode),
        "stats": stats,
        "outcome_count": len(outcomes.get("outcomes", [])),
        "assessment": stats.get("gates", {}),
    }

    REPORT_FILE.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"[report] Saved to {REPORT_FILE}")

    status = stats.get("gates", {}).get("overall", "UNKNOWN")
    print(f"[report] Overall: {status}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="A/B Harness — evaluate drift brief effectiveness")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--mode",
        choices=["mock", "llm"],
        default="mock",
        help="Agent mode (default: mock, deterministic)",
    )
    parser.add_argument(
        "--mock-mode",
        dest="mock_mode",
        choices=["biased", "neutral"],
        default="biased",
        help=(
            "Mock edit strategy. 'biased' (default): treatment arm produces structurally "
            "clean code, control arm produces duplicate handlers — guarantees high Cohen's d "
            "but measures structural bias, not brief effectiveness. "
            "'neutral': both arms produce structurally equivalent single-function edits; "
            "only naming style differs — measures actual effect of receiving a drift brief."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run", help="Run A/B experiment")
    subparsers.add_parser("stats", help="Statistical analysis")
    subparsers.add_parser("report", help="Generate summary report")

    args = parser.parse_args()
    dispatch = {
        "run": cmd_run,
        "stats": cmd_stats,
        "report": cmd_report,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
