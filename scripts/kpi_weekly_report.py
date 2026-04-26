#!/usr/bin/env python3
"""Generate a weekly KPI report from trend data.

Usage:
    python scripts/kpi_weekly_report.py                  # Current week
    python scripts/kpi_weekly_report.py --week 2026-W16  # Specific week
    python scripts/kpi_weekly_report.py --apply           # Write to file

Reads kpi_trend.jsonl and computes:
- Score trend (slope over last 4+ entries)
- Finding netto (new - resolved)
- Recurrence rate
- Precision/recall regression guard
- Health status (HEALTHY / WARNING / ALARM)
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
KPI_TREND = REPO_ROOT / "benchmark_results" / "kpi_trend.jsonl"
WEEKLY_DIR = REPO_ROOT / "work_artifacts" / "internal_eval" / "kpi" / "weekly_reports"


# ---------------------------------------------------------------------------
# Trend loading
# ---------------------------------------------------------------------------


def _load_trend() -> list[dict[str, Any]]:
    if not KPI_TREND.exists():
        return []
    lines = KPI_TREND.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _iso_week(ts_str: str) -> str:
    """Extract ISO week string (YYYY-Www) from ISO timestamp."""
    dt = datetime.fromisoformat(ts_str)
    cal = dt.isocalendar()
    return f"{cal.year}-W{cal.week:02d}"


def _current_week() -> str:
    now = datetime.now(UTC)
    cal = now.isocalendar()
    return f"{cal.year}-W{cal.week:02d}"


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def _linear_slope(values: list[float]) -> float:
    """Simple linear regression slope (least squares)."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den > 0 else 0.0


def _health_status(
    score_slope: float,
    recurrence_rate: float,
    f1: float,
    consecutive_rises: int,
) -> str:
    """Determine health status from KPI indicators."""
    if consecutive_rises >= 6 or recurrence_rate > 0.40 or f1 < 0.95:
        return "ALARM"
    if consecutive_rises >= 3 or recurrence_rate > 0.20:
        return "WARNING"
    return "HEALTHY"


def _product_health_status(
    mom_delta: float | None,
    budget_headroom_pct: float | None,
) -> str:
    """Return ALARM / WARNING / HEALTHY / NO_DATA for product health signals."""
    if mom_delta is None and budget_headroom_pct is None:
        return "NO_DATA"
    if budget_headroom_pct is not None and budget_headroom_pct < 0.10:
        return "ALARM"
    if mom_delta is not None and mom_delta < -0.30:
        return "ALARM"
    if budget_headroom_pct is not None and budget_headroom_pct < 0.30:
        return "WARNING"
    if mom_delta is not None and mom_delta < -0.20:
        return "WARNING"
    return "HEALTHY"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _build_product_health_section(
    entries: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Extract product health data from the latest trend entries.

    Returns ``None`` when no product health fields are present in the trend.
    Falls back to reading ``benchmark_results/kpi_snapshot.json`` directly
    for the ``product_health`` block if available.
    """
    from pathlib import Path as _Path  # local to avoid polluting module scope

    repo_root = _Path(__file__).resolve().parent.parent
    snapshot_path = repo_root / "benchmark_results" / "kpi_snapshot.json"

    # --- Source 1: latest trend entry compact fields ---
    latest = entries[-1] if entries else {}
    pypi_last_30d = latest.get("pypi_downloads_last_30d")
    github_stars = latest.get("github_stars")
    perf_wall_clock = latest.get("perf_wall_clock_seconds")

    # --- Source 2: full kpi_snapshot.json product_health block ---
    ph_snap: dict[str, Any] = {}
    if snapshot_path.exists():
        try:
            import json as _json

            data = _json.loads(snapshot_path.read_text(encoding="utf-8"))
            ph_snap = data.get("product_health", {})
        except Exception:  # noqa: BLE001
            pass

    # Prefer snapshot block values (more complete) over compact trend fields
    adoption_snap = ph_snap.get("adoption", {})
    perf_snap = ph_snap.get("performance", {})
    stability_snap = ph_snap.get("stability", {})

    pypi_last = adoption_snap.get("pypi_downloads_last_30d") or pypi_last_30d
    pypi_prev = adoption_snap.get("pypi_downloads_prev_30d")
    mom_delta = adoption_snap.get("pypi_downloads_mom_delta")
    stars = adoption_snap.get("github_stars") or github_stars
    forks = adoption_snap.get("github_forks")
    open_issues = stability_snap.get("open_issues")
    open_bugs = stability_snap.get("open_bugs")
    wall_clock = perf_snap.get("wall_clock_median_seconds") or perf_wall_clock
    budget_s = perf_snap.get("budget_seconds")
    headroom = perf_snap.get("budget_headroom_pct")
    collected_at = ph_snap.get("collected_at")

    # Return None when no product health data exists at all
    has_data = any(
        v is not None
        for v in [pypi_last, stars, open_issues, wall_clock]
    )
    if not has_data:
        return None

    # MoM trend from compact trend fields if snapshot didn't have it
    if mom_delta is None and len(entries) >= 2:
        prev_entry = next(
            (e for e in reversed(entries[:-1]) if e.get("pypi_downloads_last_30d") is not None),
            None,
        )
        if prev_entry and pypi_last is not None:
            prev_val = prev_entry["pypi_downloads_last_30d"]
            if prev_val and prev_val > 0:
                mom_delta = round((pypi_last - prev_val) / prev_val, 4)

    ph_status = _product_health_status(mom_delta, headroom)

    return {
        "status": ph_status,
        "collected_at": collected_at,
        "adoption": {
            "pypi_downloads_last_30d": pypi_last,
            "pypi_downloads_prev_30d": pypi_prev,
            "pypi_downloads_mom_delta": mom_delta,
            "github_stars": stars,
            "github_forks": forks,
        },
        "stability": {
            "open_issues": open_issues,
            "open_bugs": open_bugs,
        },
        "performance": {
            "wall_clock_median_seconds": wall_clock,
            "budget_seconds": budget_s,
            "budget_headroom_pct": headroom,
        },
        "thresholds": {
            "mom_delta_warning": -0.20,
            "mom_delta_alarm": -0.30,
            "budget_headroom_warning": 0.30,
            "budget_headroom_alarm": 0.10,
        },
    }


def build_weekly_report(
    entries: list[dict[str, Any]],
    week: str,
) -> dict[str, Any]:
    """Build a weekly KPI report from trend entries."""
    if not entries:
        return {
            "week": week,
            "status": "NO_DATA",
            "error": "No trend entries available",
        }

    latest = entries[-1]
    version = latest.get("version", "unknown")

    # Score trend (last 4+ entries)
    scores = [e.get("self_analysis_drift_score", 0) for e in entries]
    score_slope = _linear_slope(scores[-8:]) if len(scores) >= 2 else 0.0

    # Consecutive score rises
    consecutive_rises = 0
    for i in range(len(scores) - 1, 0, -1):
        if scores[i] > scores[i - 1]:
            consecutive_rises += 1
        else:
            break

    # Finding netto
    nettos = [e.get("finding_netto", 0) for e in entries]
    latest_netto = nettos[-1] if nettos else 0
    avg_netto = sum(nettos[-4:]) / min(len(nettos), 4) if nettos else 0

    # Recurrence
    recurrence_rates = [e.get("recurrence_rate", 0) for e in entries]
    latest_recurrence = recurrence_rates[-1] if recurrence_rates else 0

    # Precision/recall guard
    f1 = latest.get("aggregate_f1", 1.0)
    mutation_recall = latest.get("mutation_recall", 1.0)

    # Deltas vs previous entry
    prev = entries[-2] if len(entries) >= 2 else None
    score_delta = (
        (latest.get("self_analysis_drift_score", 0) - prev.get("self_analysis_drift_score", 0))
        if prev
        else 0
    )
    finding_count = latest.get("self_analysis_finding_count", 0)

    status = _health_status(score_slope, latest_recurrence, f1, consecutive_rises)

    product_health = _build_product_health_section(entries)

    report: dict[str, Any] = {
        "week": week,
        "generated_at": datetime.now(UTC).isoformat(),
        "drift_version": version,
        "git_sha": latest.get("git_sha", ""),
        "status": status,
        "self_analysis": {
            "score": latest.get("self_analysis_drift_score", 0),
            "score_delta_prev": round(score_delta, 6),
            "score_slope_4w": round(score_slope, 6),
            "consecutive_score_rises": consecutive_rises,
            "findings_total": finding_count,
            "finding_netto": latest_netto,
            "finding_netto_avg_4w": round(avg_netto, 2),
        },
        "recurrence": {
            "rate": latest_recurrence,
            "count": latest.get("recurrence_count", 0),
        },
        "precision_recall": {
            "aggregate_f1": f1,
            "mutation_recall": mutation_recall,
            "total_fixtures": latest.get("total_fixtures", 0),
        },
        "trend_entries_used": len(entries),
        "thresholds": {
            "score_slope_warning": "3 consecutive rises",
            "score_slope_alarm": "6 consecutive rises",
            "recurrence_warning": 0.20,
            "recurrence_alarm": 0.40,
            "f1_alarm": 0.95,
        },
    }
    if product_health is not None:
        report["product_health"] = product_health
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly KPI report")
    parser.add_argument("--week", default=None, help="ISO week (e.g. 2026-W16)")
    parser.add_argument("--apply", action="store_true", help="Write report to file")
    args = parser.parse_args()

    week = args.week or _current_week()
    entries = _load_trend()

    report = build_weekly_report(entries, week)

    print(json.dumps(report, indent=2, default=str))

    if args.apply:
        WEEKLY_DIR.mkdir(parents=True, exist_ok=True)
        out_path = WEEKLY_DIR / f"{week}.json"
        out_path.write_text(
            json.dumps(report, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\n[kpi] Saved to {out_path}")
    else:
        print("\n[kpi] Dry-run. Use --apply to write.")


if __name__ == "__main__":
    main()
