#!/usr/bin/env python3
"""Experiment B — Does drift flag files before bugs appear in them?

Hypothesis: Drift findings on a file correlate with later `fix:` commits
touching the same file within a 90-day window.

Method:
1. Collect all files touched by `fix:` commits in the last ``--days`` days.
2. Run ``drift analyze`` (or load a cached JSON) to get current findings
   and the files they point to.
3. Compute overlap: how many drift-flagged files also had a fix: commit?
4. Compute precision proxy: of drift-flagged files, what fraction later
   received a fix: commit?
5. Compute recall proxy: of fix: files, what fraction had a prior drift
   finding?

Output:
- Console table
- JSON report written to ``work_artifacts/experiment_b/report.json``

Usage:
    python scripts/experiment_b_bug_correlation.py
    python scripts/experiment_b_bug_correlation.py --days 90 --scan-json last_scan.json
    python scripts/experiment_b_bug_correlation.py --live   # runs drift analyze first
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_DIR = REPO_ROOT / "work_artifacts" / "experiment_b"
REPORT_FILE = WORK_DIR / "report.json"
DEFAULT_DAYS = 90
PRECISION_GOAL = 0.40  # hypothesis: >40% of drift-flagged files got a fix:


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return result.stdout.strip()


def get_fix_commits(days: int) -> list[dict]:
    """Return list of {sha, subject} for fix: commits in the last N days."""
    raw = _git(
        "log",
        f"--since={days} days ago",
        "--format=%H\t%s",
    )
    commits = []
    for line in raw.splitlines():
        if "\t" not in line:
            continue
        sha, subject = line.split("\t", 1)
        if subject.strip().startswith("fix:"):
            commits.append({"sha": sha.strip(), "subject": subject.strip()})
    return commits


def files_touched_by_commit(sha: str) -> list[str]:
    """Return POSIX-relative paths of files modified in a commit."""
    raw = _git("diff-tree", "--no-commit-id", "-r", "--name-only", sha)
    return [p.strip() for p in raw.splitlines() if p.strip()]


def collect_fix_files(commits: list[dict]) -> dict[str, list[str]]:
    """Map each POSIX file path → list of fix: commit shas that touched it."""
    file_to_fixes: dict[str, list[str]] = defaultdict(list)
    for commit in commits:
        for f in files_touched_by_commit(commit["sha"]):
            file_to_fixes[f].append(commit["sha"])
    return dict(file_to_fixes)


# ---------------------------------------------------------------------------
# Drift analysis helpers
# ---------------------------------------------------------------------------


def run_drift_analyze() -> dict[str, object]:
    """Run drift analyze --format json and return parsed output."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "drift",
            "analyze",
            "--repo",
            str(REPO_ROOT),
            "--format",
            "json",
            "--exit-zero",
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    raw = result.stdout.strip()
    # Strip non-JSON trailing content (Rich symbols etc.)
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in drift output:\n{raw[:500]}")
    return json.loads(raw[start:end])  # type: ignore[no-any-return]


def load_scan_json(path: Path) -> dict[str, object]:
    """Load a drift analyze JSON output file.

    Handles both:
    - pure JSON files (single object)
    - NDJSON / mixed output where the last ``{...}`` block is the analysis result
      (drift emits progress lines followed by the final analysis object)
    """
    content = path.read_text(encoding="utf-8")
    content = content.strip()
    # Try direct parse first
    try:
        return json.loads(content)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        pass
    # Fall back: find the last top-level JSON object
    start = content.rfind("\n{")
    if start != -1:
        start += 1
    else:
        start = content.find("{")
    end = content.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in {path}")
    return json.loads(content[start:end])  # type: ignore[no-any-return]


def extract_drift_files(scan: dict, src_only: bool = True) -> dict[str, list[str]]:
    """Map POSIX file path → list of signal_type strings from drift findings.

    Parameters
    ----------
    src_only:
        When True (default) only include files under ``src/`` to avoid noise
        from generated assets, playground/dist, etc.
    """
    file_to_signals: dict[str, list[str]] = defaultdict(list)
    findings = scan.get("findings", [])
    for finding in findings:
        # JSON output uses "file" for the primary path
        fp = (
            finding.get("file")
            or finding.get("file_path")
            or (finding.get("location") or {}).get("path")
        )
        if not fp:
            continue
        # Normalise to forward slashes relative to repo root
        try:
            rel = Path(fp).relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = Path(fp).as_posix()
        if src_only and not rel.startswith("src/"):
            continue
        signal = (
            finding.get("signal")
            or finding.get("signal_type")
            or finding.get("signal_abbrev")
            or "unknown"
        )
        file_to_signals[rel].append(signal)
    return dict(file_to_signals)


# ---------------------------------------------------------------------------
# Correlation analysis
# ---------------------------------------------------------------------------


def correlate(
    drift_files: dict[str, list[str]],
    fix_files: dict[str, list[str]],
) -> dict:
    drift_set = set(drift_files)
    fix_set = set(fix_files)
    overlap = drift_set & fix_set

    precision = len(overlap) / len(drift_set) if drift_set else 0.0
    recall = len(overlap) / len(fix_set) if fix_set else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # Per-signal breakdown for overlapping files
    signal_counts: dict[str, int] = defaultdict(int)
    for f in overlap:
        for sig in drift_files[f]:
            signal_counts[sig] += 1

    # Top offenders: files that both had drift findings AND multiple fix: commits
    top_offenders = sorted(
        [
            {
                "file": f,
                "signals": drift_files[f],
                "fix_commits": len(fix_files[f]),
            }
            for f in overlap
        ],
        key=lambda x: len(fix_files[str(x["file"])]),
        reverse=True,
    )[:10]

    return {
        "drift_flagged_files": len(drift_set),
        "fix_commit_files": len(fix_set),
        "overlap_files": len(overlap),
        "precision_proxy": round(precision, 4),
        "recall_proxy": round(recall, 4),
        "f1_proxy": round(f1, 4),
        "precision_goal": PRECISION_GOAL,
        "hypothesis_supported": precision >= PRECISION_GOAL,
        "signal_breakdown_in_overlap": dict(signal_counts),
        "top_offenders": top_offenders,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _bar(ratio: float, width: int = 30) -> str:
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def print_report(result: dict, days: int) -> None:
    c = result["correlation"]
    print()
    print("=" * 60)
    print(f"  Experiment B — Drift-Bug Correlation ({days}-day window)")
    print("=" * 60)
    print(f"  Drift-flagged files    : {c['drift_flagged_files']}")
    print(f"  Files with fix: commits: {c['fix_commit_files']}")
    print(f"  Overlap                : {c['overlap_files']}")
    print()
    prec = c["precision_proxy"]
    rec = c["recall_proxy"]
    print(f"  Precision proxy  {prec:5.1%}  {_bar(prec)}")
    print(f"  Recall proxy     {rec:5.1%}  {_bar(rec)}")
    print(f"  F1 proxy         {c['f1_proxy']:5.1%}")
    print()
    if c["hypothesis_supported"]:
        print(f"  ✓ HYPOTHESIS SUPPORTED  (precision {prec:.1%} >= goal {c['precision_goal']:.0%})")
    else:
        print(f"  ✗ HYPOTHESIS NOT MET    (precision {prec:.1%} < goal {c['precision_goal']:.0%})")
    print()
    print("  Signal breakdown in overlapping files:")
    for sig, cnt in sorted(c["signal_breakdown_in_overlap"].items(), key=lambda x: -x[1])[:8]:
        print(f"    {sig:<30} {cnt:>4}")
    print()
    print("  Top 5 offenders (drift-flagged + most fix: commits):")
    for item in c["top_offenders"][:5]:
        sigs = ", ".join(sorted(set(item["signals"])))
        print(f"    [{item['fix_commits']} fixes]  {item['file']}")
        print(f"              signals: {sigs}")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Experiment B — drift-bug correlation")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS, help="Look-back window in days")
    parser.add_argument(
        "--scan-json",
        default=None,
        help="Path to existing drift analyze JSON output (skips live run)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        default=False,
        help="Run drift analyze live (ignores --scan-json)",
    )
    parser.add_argument(
        "--output",
        default=str(REPORT_FILE),
        help="Output path for JSON report",
    )
    args = parser.parse_args(argv)

    print(f"[Experiment B] Collecting fix: commits from last {args.days} days…")
    fix_commits = get_fix_commits(args.days)
    print(f"  Found {len(fix_commits)} fix: commits")

    print("[Experiment B] Mapping touched files…")
    fix_files = collect_fix_files(fix_commits)
    print(f"  {len(fix_files)} unique files touched by fix: commits")

    if args.live:
        print("[Experiment B] Running drift analyze (live)…")
        scan = run_drift_analyze()
    elif args.scan_json:
        scan_path = Path(args.scan_json)
        if not scan_path.is_absolute():
            scan_path = REPO_ROOT / scan_path
        print(f"[Experiment B] Loading scan from {scan_path}…")
        scan = load_scan_json(scan_path)
    else:
        default_scan = REPO_ROOT / "last_scan.json"
        if default_scan.exists():
            print(f"[Experiment B] Loading scan from {default_scan}…")
            scan = load_scan_json(default_scan)
        else:
            print("[Experiment B] No scan JSON found. Running drift analyze (live)…")
            scan = run_drift_analyze()

    drift_files = extract_drift_files(scan, src_only=True)
    # Also restrict fix_files to src/ for a fair comparison
    fix_files_src = {k: v for k, v in fix_files.items() if k.startswith("src/")}
    print(f"  {len(drift_files)} files with drift findings (src/ only)")
    total = len(fix_files)
    print(f"  {len(fix_files_src)} files touched by fix: commits (src/ only, of {total} total)")

    result = {
        "schema_version": "1.0",
        "experiment": "B",
        "generated_at": datetime.now(UTC).isoformat(),
        "window_days": args.days,
        "fix_commit_count": len(fix_commits),
        "correlation": correlate(drift_files, fix_files_src),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"[Experiment B] Report written → {output_path}")

    print_report(result, args.days)

    return 0 if result["correlation"]["hypothesis_supported"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
