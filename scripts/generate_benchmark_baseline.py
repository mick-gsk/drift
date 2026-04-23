#!/usr/bin/env python3
"""Generate and compare benchmark baseline KPI snapshot.

Reads:
  benchmark_results/mutation_benchmark.json  -> overall_recall (kill score)
  benchmark_results/ground_truth_analysis.json -> precision_lenient per signal

Runs:
  drift analyze --repo . --format json --exit-zero -> drift_score, grade, findings_count

Writes:
  benchmark_results/perf_baseline_latest.json

Exit codes:
  0 = ok / baseline established
  1 = regression detected (only when --compare-previous)
  2 = error (missing input files)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
MUTATION_JSON = REPO_ROOT / "benchmark_results" / "mutation_benchmark.json"
GROUND_TRUTH_JSON = REPO_ROOT / "benchmark_results" / "ground_truth_analysis.json"
BASELINE_JSON = REPO_ROOT / "benchmark_results" / "perf_baseline_latest.json"

# Threshold (percentage points) at which a drop is a regression
REGRESSION_THRESHOLD_PP = 5.0


def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _drift_analyze() -> tuple[float | None, str | None, int | None]:
    """Run drift analyze and return (drift_score, grade, findings_count)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "drift", "analyze", "--repo", ".", "--format", "json", "--exit-zero"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=120,
        )
        raw = result.stdout
        # Extract JSON content (guard against trailing Rich symbols)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end <= start:
            print(f"[warn] Could not parse drift analyze output:\n{raw[:200]}", file=sys.stderr)
            return None, None, None
        data = json.loads(raw[start:end])
        score = data.get("drift_score")
        grade = data.get("grade")
        count = data.get("compact_summary", {}).get("findings_total") or data.get("total_findings")
        return score, grade, count
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] drift analyze failed: {exc}", file=sys.stderr)
        return None, None, None


def _load_mutation() -> float | None:
    if not MUTATION_JSON.exists():
        print(f"[warn] {MUTATION_JSON} not found — skipping mutation KPI", file=sys.stderr)
        return None
    data = _load_json(MUTATION_JSON)
    return data.get("overall_recall")


def _load_precision() -> tuple[float | None, dict]:
    if not GROUND_TRUTH_JSON.exists():
        print(f"[warn] {GROUND_TRUTH_JSON} not found — skipping precision KPI", file=sys.stderr)
        return None, {}
    data = _load_json(GROUND_TRUTH_JSON)
    by_signal = data.get("precision_by_signal", {})
    values = [
        v["precision_lenient"]
        for v in by_signal.values()
        if isinstance(v.get("precision_lenient"), (int, float))
    ]
    avg = sum(values) / len(values) if values else None
    return avg, {sig: v.get("precision_lenient") for sig, v in by_signal.items()}


def _read_previous_baseline() -> dict | None:
    """Try reading the committed (HEAD) version of perf_baseline_latest.json via git."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD:benchmark_results/perf_baseline_latest.json"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=15,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception:  # noqa: BLE001
        pass
    return None


def _open_regression_issue(details: str, sha: str) -> None:
    """Call gh CLI to open a GitHub Issue for the regression."""
    body = (
        f"## Benchmark Regression Detected\n\n"
        f"Commit: `{sha}`\n\n"
        f"{details}\n\n"
        f"Triggered by `benchmark-baseline-loop.yml`.\n"
        f"Please review `benchmark_results/perf_baseline_latest.json` and the mutation benchmark."
    )
    try:
        subprocess.run(
            [
                "gh", "issue", "create",
                "--title", f"Benchmark regression detected at {sha[:8]}",
                "--label", "benchmark-regression",
                "--body", body,
            ],
            check=True,
            cwd=str(REPO_ROOT),
        )
        print("Opened GitHub issue for regression.")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] Could not open issue: {exc}", file=sys.stderr)
    try:
        result = subprocess.run(
            ["gh", "issue", "list", "--label", "benchmark-regression", "--state", "open", "--json", "number", "--limit", "1"],
            capture_output=True, text=True, cwd=str(REPO_ROOT),
        )
        items = json.loads(result.stdout or "[]")
        if items:
            num = items[0]["number"]
            subprocess.run(
                ["gh", "issue", "edit", str(num), "--add-assignee", "copilot"],
                cwd=str(REPO_ROOT),
            )
    except Exception:  # noqa: BLE001
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-previous", action="store_true",
                        help="Compare new KPIs against previous baseline; exit 1 on regression")
    parser.add_argument("--gh-issue-on-regression", action="store_true",
                        help="Open a GitHub issue when regression detected (requires gh CLI)")
    parser.add_argument("--skip-drift-analyze", action="store_true",
                        help="Skip running drift analyze (use when drift is not available)")
    args = parser.parse_args()

    sha = os.environ.get("GITHUB_SHA", "local")
    ref_name = os.environ.get("GITHUB_REF_NAME", "local")

    print("=== Benchmark Baseline Generator ===")
    print(f"SHA={sha[:12]}  ref={ref_name}")

    # Collect KPIs
    overall_recall = _load_mutation()
    precision_avg, precision_by_signal = _load_precision()
    drift_score, grade, findings_count = (None, None, None) if args.skip_drift_analyze else _drift_analyze()

    now = datetime.now(timezone.utc).isoformat()
    baseline = {
        "_metadata": {
            "generated_at": now,
            "generated_by": "benchmark-baseline-loop",
            "sha": sha,
            "ref": ref_name,
        },
        "version": None,  # set by CI if available
        "sha": sha,
        "drift_score": drift_score,
        "grade": grade,
        "findings_count": findings_count,
        "overall_recall": overall_recall,
        "precision_lenient_avg": precision_avg,
        "precision_by_signal": precision_by_signal,
    }

    # Optionally read pyproject.toml version
    try:
        import tomllib  # type: ignore[import]
        with open(REPO_ROOT / "pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        baseline["version"] = pyproject.get("project", {}).get("version")
    except Exception:  # noqa: BLE001
        pass

    # Write baseline
    BASELINE_JSON.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_JSON.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"Wrote {BASELINE_JSON}")
    print(f"  drift_score={drift_score}  grade={grade}  findings={findings_count}")
    print(f"  overall_recall={overall_recall}  precision_lenient_avg={precision_avg}")

    if not args.compare_previous:
        return 0

    # Compare against previous
    previous = _read_previous_baseline()
    if previous is None or previous.get("overall_recall") is None:
        print("[info] No previous baseline with data found — establishing baseline.")
        return 0

    regression_messages: list[str] = []

    def _check(name: str, new_val: float | None, prev_val: float | None) -> None:
        if new_val is None or prev_val is None:
            return
        delta_pp = (new_val - prev_val) * 100.0
        status = "OK" if delta_pp >= -REGRESSION_THRESHOLD_PP else "REGRESSION"
        print(f"  {name}: {prev_val:.3f} -> {new_val:.3f}  ({delta_pp:+.1f}pp)  [{status}]")
        if status == "REGRESSION":
            regression_messages.append(
                f"- **{name}**: {prev_val:.3f} -> {new_val:.3f} ({delta_pp:+.1f}pp)"
            )

    print("\n--- KPI comparison ---")
    _check("overall_recall", overall_recall, previous.get("overall_recall"))
    _check("precision_lenient_avg", precision_avg, previous.get("precision_lenient_avg"))
    _check("drift_score (inverted)", 1.0 - (drift_score or 0), 1.0 - (previous.get("drift_score") or 0))

    if regression_messages:
        details = "\n".join(regression_messages)
        print(f"\n[REGRESSION] Thresholds exceeded:\n{details}")
        if args.gh_issue_on_regression:
            _open_regression_issue(details, sha)
        return 1

    print("\nAll KPIs within threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
