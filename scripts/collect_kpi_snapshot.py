#!/usr/bin/env python3
"""Collect a KPI snapshot and append it to kpi_trend.jsonl.

Gathers quality metrics from up to four sources:
  1. Precision/Recall evaluation (ground-truth fixtures)
  2. Mutation benchmark results (if JSON exists)
  3. Self-analysis finding count (if JSON exists)
  4. Product health: PyPI downloads + GitHub stats + perf wall clock (opt-in)

Usage:
    python scripts/collect_kpi_snapshot.py [--output benchmark_results/kpi_snapshot.json]
    python scripts/collect_kpi_snapshot.py --product-health          # adds product_health section
    python scripts/collect_kpi_snapshot.py --product-health --include-perf-run  # also measures perf

The snapshot is also appended as a single line to benchmark_results/kpi_trend.jsonl.
"""

from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent.parent
TREND_FILE = REPO_ROOT / "benchmark_results" / "kpi_trend.jsonl"
MUTATION_FILE = REPO_ROOT / "benchmark_results" / "mutation_benchmark.json"
PERF_BUDGET_FILE = REPO_ROOT / "benchmarks" / "perf_budget.json"
_PYPI_PACKAGE = "drift-analyzer"
_GITHUB_REPO = "mick-gsk/drift"


def _get_version() -> str:
    """Read the current drift version from pyproject.toml."""
    pyproject = REPO_ROOT / "pyproject.toml"
    for line in pyproject.read_text(encoding="utf-8").splitlines():
        if line.startswith("version"):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "unknown"


def _get_git_sha() -> str:
    """Return short git SHA of HEAD."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def collect_precision_recall() -> dict:
    """Run ground-truth evaluation and return per-signal + aggregate metrics."""
    # Import locally to avoid top-level dependency issues in CI
    sys.path.insert(0, str(REPO_ROOT / "tests"))
    sys.path.insert(0, str(REPO_ROOT / "src"))

    from drift.precision import ensure_signals_registered, evaluate_fixtures

    from fixtures.ground_truth import ALL_FIXTURES

    ensure_signals_registered()

    with tempfile.TemporaryDirectory() as tmp:
        report, _warnings = evaluate_fixtures(ALL_FIXTURES, Path(tmp))

    data = report.to_dict()
    # Flatten per-signal to just P/R/F1 for trend tracking
    per_signal = {}
    for sig_name, sig_data in data["signals"].items():
        per_signal[sig_name] = {
            "precision": sig_data["precision"],
            "recall": sig_data["recall"],
            "f1": sig_data["f1"],
            "tp": sig_data["tp"],
            "fp": sig_data["fp"],
            "fn": sig_data["fn"],
            "tn": sig_data["tn"],
        }

    return {
        "aggregate_f1": data["aggregate_f1"],
        "total_fixtures": data["total_fixtures"],
        "signals": per_signal,
    }


def collect_mutation_recall() -> dict | None:
    """Read mutation benchmark results if they exist."""
    if not MUTATION_FILE.exists():
        return None
    data = json.loads(MUTATION_FILE.read_text(encoding="utf-8"))
    per_signal = {}
    detection = data.get("detection", {})
    for sig_name, sig_data in detection.items():
        per_signal[sig_name] = {
            "injected": sig_data["injected"],
            "detected": sig_data["detected"],
            "recall": sig_data["recall"],
        }
    return {
        "overall_recall": data.get("overall_recall", 0.0),
        "total_injected": data.get("total_injected", 0),
        "total_detected": data.get("total_detected", 0),
        "signals": per_signal,
    }


def collect_self_analysis_count() -> int | None:
    """Run drift self-analysis and return finding count."""
    try:
        cmd = [
            sys.executable, "-m", "drift", "analyze",
            "--repo", ".", "--format", "json", "--exit-zero",
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=120,
        )
        if result.returncode != 0:
            return None
        # Parse NDJSON — find the result object
        decoder = json.JSONDecoder()
        text = result.stdout
        idx = 0
        findings_count = None
        while idx < len(text):
            try:
                obj, end = decoder.raw_decode(text, idx)
                idx = end
                if isinstance(obj, dict) and "findings" in obj:
                    findings_count = len(obj["findings"])
                    break
            except json.JSONDecodeError:
                idx += 1
        return findings_count
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Product health collection (opt-in)
# ---------------------------------------------------------------------------


def _fetch_pypi_downloads(
    package: str = _PYPI_PACKAGE,
    timeout: int = 20,
) -> dict[str, object] | None:
    """Return download counts for the last two calendar months from PyPIStats.

    Returns a dict with ``last_30d``, ``prev_30d``, ``mom_delta`` or ``None``
    on any network/parse error.
    """
    url = f"https://pypistats.org/api/packages/{package}/overall?mirrors=false"
    request = Request(url, headers={"User-Agent": "drift-kpi-snapshot/1"})
    try:
        with urlopen(request, timeout=timeout) as resp:  # noqa: S310  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
    except (HTTPError, URLError, OSError):
        return None

    rows: list[dict[str, object]] = payload.get("data", [])
    monthly: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("category") not in {"without_mirrors", "overall"}:
            continue
        date_str = str(row.get("date", ""))
        month = date_str[:7]
        if len(month) != 7 or month[4] != "-":
            continue
        try:
            monthly[month] += int(str(row.get("downloads", 0)))
        except (TypeError, ValueError):
            continue

    sorted_months = sorted(monthly.keys())
    if not sorted_months:
        return None

    last_month = sorted_months[-1]
    prev_month = sorted_months[-2] if len(sorted_months) >= 2 else None

    last_30d: int = monthly[last_month]
    prev_30d: int | None = monthly[prev_month] if prev_month else None
    mom_delta: float | None = None
    if prev_30d is not None and prev_30d > 0:
        mom_delta = round((last_30d - prev_30d) / prev_30d, 4)

    return {
        "last_30d": last_30d,
        "prev_30d": prev_30d,
        "mom_delta": mom_delta,
    }


def _fetch_perf_wall_clock() -> dict[str, object] | None:
    """Run perf_gate.py with --json and return wall-clock metrics.

    Reads the budget from ``benchmarks/perf_budget.json``.
    Returns ``None`` on subprocess error or if perf_gate.py is missing.
    """
    perf_gate = REPO_ROOT / "scripts" / "perf_gate.py"
    if not perf_gate.exists():
        return None

    budget = 30.0
    if PERF_BUDGET_FILE.exists():
        try:
            budget_data = json.loads(PERF_BUDGET_FILE.read_text(encoding="utf-8"))
            budget = float(budget_data.get("wall_clock_budget_seconds", 30.0))
        except (json.JSONDecodeError, ValueError):
            pass

    try:
        result = subprocess.run(
            [
                sys.executable,
                str(perf_gate),
                "--json",
                "--runs", "1",
                "--warmup", "0",
                "--budget", str(int(budget)),
                "--target-path", "src/drift",
            ],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=90,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode not in (0, 1):  # 0=pass, 1=budget exceeded — both valid
        return None

    # perf_gate may print non-JSON preamble; find the JSON object
    text = result.stdout
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        return None

    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError:
        return None

    wall_clock = data.get("wall_clock_seconds") or data.get("median")
    if wall_clock is None:
        return None

    headroom = round(1.0 - float(wall_clock) / budget, 4) if budget > 0 else None
    return {
        "wall_clock_median_seconds": round(float(wall_clock), 3),
        "budget_seconds": budget,
        "budget_headroom_pct": headroom,
    }


def collect_product_health(
    *,
    include_perf_run: bool = False,
    github_repo: str = _GITHUB_REPO,
    pypi_package: str = _PYPI_PACKAGE,
    bug_label: str = "bug",
) -> dict[str, object]:
    """Collect product-level health metrics from PyPI, GitHub, and perf gate.

    All individual sources are collected with graceful fallback — a source
    failure sets its values to ``None`` rather than raising an exception.

    Returns a dict with an ``adoption``, ``performance``, and ``stability``
    sub-section plus a ``collected_at`` timestamp.
    """
    # Import here to avoid circular issues at module load time
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from fetch_github_stats import fetch_github_stats  # type: ignore[import]

    pypi = _fetch_pypi_downloads(package=pypi_package)
    gh = fetch_github_stats(github_repo, bug_label=bug_label)
    perf = _fetch_perf_wall_clock() if include_perf_run else None

    adoption: dict[str, object] = {
        "pypi_downloads_last_30d": pypi["last_30d"] if pypi else None,
        "pypi_downloads_prev_30d": pypi["prev_30d"] if pypi else None,
        "pypi_downloads_mom_delta": pypi["mom_delta"] if pypi else None,
        "github_stars": gh["stars"] if gh else None,
        "github_forks": gh["forks"] if gh else None,
    }
    stability: dict[str, object] = {
        "open_issues": gh["open_issues"] if gh else None,
        "open_bugs": gh["open_bugs"] if gh else None,
    }
    performance: dict[str, object]
    if perf:
        performance = {
            "wall_clock_median_seconds": perf["wall_clock_median_seconds"],
            "budget_seconds": perf["budget_seconds"],
            "budget_headroom_pct": perf["budget_headroom_pct"],
        }
    else:
        performance = {
            "wall_clock_median_seconds": None,
            "budget_seconds": None,
            "budget_headroom_pct": None,
        }

    return {
        "collected_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "adoption": adoption,
        "performance": performance,
        "stability": stability,
    }


# ---------------------------------------------------------------------------
# Snapshot assembly
# ---------------------------------------------------------------------------


def build_snapshot(
    *,
    skip_self_analysis: bool = False,
    include_product_health: bool = False,
    include_perf_run: bool = False,
) -> dict:
    """Build a complete KPI snapshot."""
    snapshot: dict = {
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "version": _get_version(),
        "git_sha": _get_git_sha(),
    }

    # 1. Precision/Recall
    pr_data = collect_precision_recall()
    snapshot["precision_recall"] = {
        "aggregate_f1": pr_data["aggregate_f1"],
        "total_fixtures": pr_data["total_fixtures"],
        "signals": pr_data["signals"],
    }

    # 2. Mutation Recall
    mutation_data = collect_mutation_recall()
    if mutation_data is not None:
        snapshot["mutation"] = mutation_data

    # 3. Self-analysis finding count
    if not skip_self_analysis:
        count = collect_self_analysis_count()
        if count is not None:
            snapshot["self_analysis_finding_count"] = count

    # 4. Product health (opt-in)
    if include_product_health:
        snapshot["product_health"] = collect_product_health(
            include_perf_run=include_perf_run,
        )

    return snapshot


def append_to_trend(snapshot: dict) -> None:
    """Append a compact snapshot line to kpi_trend.jsonl."""
    # Compact representation for trend: no per-signal detail
    trend_entry = {
        "timestamp": snapshot["timestamp"],
        "version": snapshot["version"],
        "git_sha": snapshot["git_sha"],
        "aggregate_f1": snapshot["precision_recall"]["aggregate_f1"],
        "total_fixtures": snapshot["precision_recall"]["total_fixtures"],
    }
    if "mutation" in snapshot:
        trend_entry["mutation_recall"] = snapshot["mutation"]["overall_recall"]
        trend_entry["mutation_injected"] = snapshot["mutation"]["total_injected"]
    if "self_analysis_finding_count" in snapshot:
        trend_entry["self_analysis_finding_count"] = snapshot["self_analysis_finding_count"]

    # Per-signal F1 as flat dict
    trend_entry["per_signal_f1"] = {
        sig: data["f1"]
        for sig, data in snapshot["precision_recall"]["signals"].items()
    }

    # Compact product_health fields for trend (if present)
    if "product_health" in snapshot:
        ph = snapshot["product_health"]
        adoption = ph.get("adoption", {})
        performance = ph.get("performance", {})
        if adoption.get("pypi_downloads_last_30d") is not None:
            trend_entry["pypi_downloads_last_30d"] = adoption["pypi_downloads_last_30d"]
        if adoption.get("github_stars") is not None:
            trend_entry["github_stars"] = adoption["github_stars"]
        if performance.get("wall_clock_median_seconds") is not None:
            trend_entry["perf_wall_clock_seconds"] = performance["wall_clock_median_seconds"]

    TREND_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TREND_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(trend_entry, separators=(",", ":")) + "\n")


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Collect KPI snapshot")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "benchmark_results" / "kpi_snapshot.json",
        help="Path for full snapshot JSON (default: benchmark_results/kpi_snapshot.json)",
    )
    parser.add_argument(
        "--skip-self-analysis",
        action="store_true",
        help="Skip self-analysis (faster, for CI where self-analysis runs separately)",
    )
    parser.add_argument(
        "--no-trend",
        action="store_true",
        help="Do not append to kpi_trend.jsonl",
    )
    parser.add_argument(
        "--product-health",
        action="store_true",
        help="Collect product health metrics (PyPI downloads + GitHub stats)",
    )
    parser.add_argument(
        "--include-perf-run",
        action="store_true",
        help="Run perf_gate.py as part of product health collection (~8s overhead)",
    )
    args = parser.parse_args()

    print("Collecting KPI snapshot...")
    snapshot = build_snapshot(
        skip_self_analysis=args.skip_self_analysis,
        include_product_health=args.product_health,
        include_perf_run=args.include_perf_run,
    )

    # Write full snapshot
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshot written to {args.output}")

    # Append to trend
    if not args.no_trend:
        append_to_trend(snapshot)
        print(f"Trend appended to {TREND_FILE}")

    # Summary
    pr = snapshot["precision_recall"]
    print(f"\n  Aggregate F1: {pr['aggregate_f1']:.4f}")
    print(f"  Fixtures:     {pr['total_fixtures']}")
    if "mutation" in snapshot:
        m = snapshot["mutation"]
        detected = m['total_detected']
        injected = m['total_injected']
        print(f"  Mutation:     {m['overall_recall']:.2%} ({detected}/{injected})")
    if "self_analysis_finding_count" in snapshot:
        print(f"  Self-findings: {snapshot['self_analysis_finding_count']}")


if __name__ == "__main__":
    main()
