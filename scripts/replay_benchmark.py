#!/usr/bin/env python3
"""Historical Replay Benchmark — correlate Drift findings with bug-fix density.

Usage:
    python scripts/replay_benchmark.py corpus         # Build corpus manifest
    python scripts/replay_benchmark.py replay         # Run drift on all snapshots
    python scripts/replay_benchmark.py annotate       # Annotate bug-fixes
    python scripts/replay_benchmark.py correlate      # Compute correlations
    python scripts/replay_benchmark.py run            # Full pipeline
    python scripts/replay_benchmark.py --dry-run run  # Dry-run (no clones)

Hypothesis: Drift findings on historical repo snapshots correlate with
bug-fix density in the following 30/60/90 days.

Evidence target: Spearman ρ ≥ 0.25 on ≥3/5 repos (H3 — prädiktive Validität).
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ORACLE_REPOS = REPO_ROOT / "benchmarks" / "oracle_repos.json"
WORK_DIR = REPO_ROOT / "work_artifacts" / "internal_eval" / "replay"
RESULTS_DIR = WORK_DIR / "results"
PYTHON = sys.executable

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_REPOS = ["requests", "click", "flask"]  # Start small, extend later
SNAPSHOTS_PER_REPO = 15  # Equidistant over time range
TIME_RANGE_DAYS = 730  # 2 years lookback
BUGFIX_WINDOWS = [30, 60, 90]  # Days after snapshot


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class RepoConfig:
    name: str
    url: str
    ref: str = "main"
    snapshots: int = SNAPSHOTS_PER_REPO
    time_range_days: int = TIME_RANGE_DAYS


@dataclass
class SnapshotResult:
    repo: str
    sha: str
    date: str
    drift_score: float
    finding_count: int
    findings_per_file: dict[str, int] = field(default_factory=dict)
    findings_per_signal: dict[str, int] = field(default_factory=dict)


@dataclass
class BugFixAnnotation:
    repo: str
    sha: str
    date: str
    window_days: int
    bugfix_commits: int
    bugfix_files: dict[str, int] = field(default_factory=dict)  # file → count


@dataclass
class CorrelationResult:
    repo: str
    window_days: int
    spearman_rho: float
    p_value: float
    n_files: int
    relative_risk: float
    per_signal: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr[:500]}")
    return result.stdout.strip()


def _clone_or_update(url: str, dest: Path, ref: str = "main") -> None:
    """Clone repo or update existing clone."""
    if (dest / ".git").exists():
        _run_git(["fetch", "--all"], cwd=dest)
        _run_git(["checkout", ref], cwd=dest)
        _run_git(["pull", "--ff-only"], cwd=dest)
    else:
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--no-single-branch", url, str(dest)],
            check=True,
            capture_output=True,
            text=True,
        )
        _run_git(["checkout", ref], cwd=dest)


def _get_snapshot_shas(
    repo_dir: Path,
    n_snapshots: int,
    time_range_days: int,
) -> list[tuple[str, str]]:
    """Get equidistant commit SHAs over time range.

    Returns list of (sha, iso_date) tuples.
    """
    since = (datetime.now(UTC) - timedelta(days=time_range_days)).isoformat()
    log = _run_git(
        ["log", f"--since={since}", "--format=%H %aI", "--reverse"],
        cwd=repo_dir,
    )
    lines = [l for l in log.splitlines() if l.strip()]
    if not lines:
        return []

    # Pick equidistant samples
    step = max(1, len(lines) // n_snapshots)
    selected = lines[::step][:n_snapshots]

    result = []
    for line in selected:
        parts = line.split(maxsplit=1)
        if len(parts) == 2:
            result.append((parts[0], parts[1]))
    return result


def _get_bugfix_commits(
    repo_dir: Path,
    after_date: str,
    window_days: int,
) -> list[tuple[str, str, list[str]]]:
    """Find bug-fix commits in a time window after a date.

    Returns list of (sha, date, [files]) tuples.
    """
    dt = datetime.fromisoformat(after_date)
    since = dt.isoformat()
    until = (dt + timedelta(days=window_days)).isoformat()

    # Heuristic: commit messages containing fix/bug/patch/closes/fixes
    log = _run_git(
        [
            "log",
            f"--since={since}",
            f"--until={until}",
            "--format=%H %aI",
            "--grep=fix\\|bug\\|patch\\|closes #\\|fixes #",
            "-i",
            "--name-only",
        ],
        cwd=repo_dir,
    )

    commits: list[tuple[str, str, list[str]]] = []
    current_sha = ""
    current_date = ""
    current_files: list[str] = []

    for line in log.splitlines():
        if not line.strip():
            if current_sha:
                commits.append((current_sha, current_date, current_files))
                current_sha = ""
                current_date = ""
                current_files = []
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and len(parts[0]) == 40:
            if current_sha:
                commits.append((current_sha, current_date, current_files))
            current_sha = parts[0]
            current_date = parts[1]
            current_files = []
        else:
            # File path
            current_files.append(line.strip())

    if current_sha:
        commits.append((current_sha, current_date, current_files))

    return commits


# ---------------------------------------------------------------------------
# Drift analysis
# ---------------------------------------------------------------------------


def _run_drift_on_checkout(repo_dir: Path, sha: str) -> dict[str, Any]:
    """Checkout SHA, run drift, return JSON output."""
    _run_git(["checkout", sha, "--force"], cwd=repo_dir)

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


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


def _spearman_rank(x: list[float], y: list[float]) -> tuple[float, float]:
    """Compute Spearman rank correlation coefficient and approximate p-value.

    Uses scipy if available, otherwise falls back to manual calculation.
    """
    try:
        from scipy.stats import spearmanr  # noqa: PLC0415

        rho, p = spearmanr(x, y)
        return (float(rho), float(p))
    except ImportError:
        pass

    # Manual Spearman (no scipy)
    n = len(x)
    if n < 3:
        return (0.0, 1.0)

    def _rank(values: list[float]) -> list[float]:
        indexed = sorted(enumerate(values), key=lambda t: t[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n - 1 and indexed[j + 1][1] == indexed[j][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _rank(x)
    ry = _rank(y)

    d_sq = sum((a - b) ** 2 for a, b in zip(rx, ry))
    rho = 1 - (6 * d_sq) / (n * (n * n - 1))

    # Approximate p-value using t-distribution
    if abs(rho) >= 1.0:
        p = 0.0
    else:
        t_stat = rho * math.sqrt((n - 2) / (1 - rho * rho))
        # Rough two-tailed p from t-distribution (approximation)
        p = 2 * (1 - _t_cdf_approx(abs(t_stat), n - 2))

    return (rho, max(0.0, p))


def _t_cdf_approx(t: float, df: int) -> float:
    """Rough approximation of t-distribution CDF."""
    # Use normal approximation for df > 30
    if df > 30:
        return _norm_cdf(t)
    # Crude approximation
    x = df / (df + t * t)
    return 1 - 0.5 * x ** (df / 2)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _relative_risk(
    finding_files: set[str],
    bugfix_files: dict[str, int],
    all_files: set[str],
) -> float:
    """Compute relative risk: P(bugfix | finding) / P(bugfix | no finding)."""
    no_finding_files = all_files - finding_files
    if not finding_files or not no_finding_files:
        return 0.0

    bugfix_in_finding = sum(1 for f in finding_files if bugfix_files.get(f, 0) > 0)
    bugfix_in_no_finding = sum(1 for f in no_finding_files if bugfix_files.get(f, 0) > 0)

    p_finding = bugfix_in_finding / len(finding_files)
    p_no_finding = bugfix_in_no_finding / len(no_finding_files) if no_finding_files else 0

    return p_finding / p_no_finding if p_no_finding > 0 else float("inf")


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


def load_oracle_repos() -> list[RepoConfig]:
    """Load repos from oracle_repos.json, filtered to DEFAULT_REPOS."""
    data = json.loads(ORACLE_REPOS.read_text(encoding="utf-8"))
    repos = []
    for r in data["repos"]:
        if r["name"] in DEFAULT_REPOS:
            repos.append(
                RepoConfig(
                    name=r["name"],
                    url=r["url"],
                    ref=r.get("ref", "main"),
                )
            )
    return repos


def cmd_corpus(args: argparse.Namespace) -> None:
    """Build corpus manifest with snapshot SHAs."""
    repos = load_oracle_repos()
    clone_dir = Path(args.clone_dir)

    manifest: dict[str, Any] = {
        "version": "1.0.0",
        "created": datetime.now(UTC).isoformat(),
        "repos": [],
    }

    for repo in repos:
        print(f"[replay] Processing {repo.name}...")
        repo_dir = clone_dir / repo.name

        if not args.dry_run:
            _clone_or_update(repo.url, repo_dir, repo.ref)
            snapshots = _get_snapshot_shas(repo_dir, repo.snapshots, repo.time_range_days)
        else:
            snapshots = [("dry_run_sha", "2025-01-01T00:00:00+00:00")]

        manifest["repos"].append(
            {
                "name": repo.name,
                "url": repo.url,
                "ref": repo.ref,
                "snapshots": [{"sha": s[0], "date": s[1]} for s in snapshots],
            }
        )
        print(f"  → {len(snapshots)} snapshots selected")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = WORK_DIR / "corpus_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[replay] Manifest saved to {manifest_path}")


def cmd_replay(args: argparse.Namespace) -> None:
    """Run drift analyze on each snapshot."""
    manifest_path = WORK_DIR / "corpus_manifest.json"
    if not manifest_path.exists():
        print("ERROR: Run 'corpus' first to build manifest.", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clone_dir = Path(args.clone_dir)

    for repo_data in manifest["repos"]:
        repo_name = repo_data["name"]
        repo_dir = clone_dir / repo_name
        repo_results_dir = RESULTS_DIR / repo_name
        repo_results_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[replay] Replaying {repo_name} ({len(repo_data['snapshots'])} snapshots)...")

        for snap in repo_data["snapshots"]:
            sha = snap["sha"]
            out_file = repo_results_dir / f"{sha[:12]}.json"

            if out_file.exists() and not args.force:
                print(f"  ✓ {sha[:12]} (cached)")
                continue

            if args.dry_run:
                print(f"  → {sha[:12]} (dry-run, skipped)")
                continue

            print(f"  → {sha[:12]}...", end=" ", flush=True)
            try:
                result = _run_drift_on_checkout(repo_dir, sha)
                findings = result.get("findings", [])

                # Extract per-file finding counts
                per_file: dict[str, int] = {}
                per_signal: dict[str, int] = {}
                for f in findings:
                    fpath = f.get("file", "unknown")
                    per_file[fpath] = per_file.get(fpath, 0) + 1
                    sig = f.get("signal_type", f.get("signal", "unknown"))
                    per_signal[sig] = per_signal.get(sig, 0) + 1

                snapshot_result = {
                    "repo": repo_name,
                    "sha": sha,
                    "date": snap["date"],
                    "drift_score": result.get("drift_score", 0),
                    "finding_count": len(findings),
                    "findings_per_file": per_file,
                    "findings_per_signal": per_signal,
                }

                out_file.write_text(
                    json.dumps(snapshot_result, indent=2, default=str),
                    encoding="utf-8",
                )
                print(f"score={result.get('drift_score', 0):.3f}, findings={len(findings)}")
            except Exception as exc:
                print(f"ERROR: {exc}")

        # Restore to default ref
        if not args.dry_run and repo_dir.exists():
            _run_git(["checkout", repo_data.get("ref", "main"), "--force"], cwd=repo_dir)


def cmd_annotate(args: argparse.Namespace) -> None:
    """Annotate bug-fix commits for each snapshot's look-ahead window."""
    manifest_path = WORK_DIR / "corpus_manifest.json"
    if not manifest_path.exists():
        print("ERROR: Run 'corpus' first.", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    clone_dir = Path(args.clone_dir)

    annotations: list[dict[str, Any]] = []

    for repo_data in manifest["repos"]:
        repo_name = repo_data["name"]
        repo_dir = clone_dir / repo_name

        if not repo_dir.exists():
            print(f"[annotate] SKIP {repo_name}: not cloned")
            continue

        # Restore main branch for log queries
        _run_git(["checkout", repo_data.get("ref", "main"), "--force"], cwd=repo_dir)

        print(f"\n[annotate] {repo_name} ({len(repo_data['snapshots'])} snapshots)...")

        for snap in repo_data["snapshots"]:
            for window in BUGFIX_WINDOWS:
                if args.dry_run:
                    continue

                bugfixes = _get_bugfix_commits(repo_dir, snap["date"], window)
                file_counts: dict[str, int] = {}
                for _sha, _date, files in bugfixes:
                    for f in files:
                        file_counts[f] = file_counts.get(f, 0) + 1

                annotations.append(
                    {
                        "repo": repo_name,
                        "sha": snap["sha"],
                        "date": snap["date"],
                        "window_days": window,
                        "bugfix_commits": len(bugfixes),
                        "bugfix_files": file_counts,
                    }
                )

    ann_path = WORK_DIR / "bugfix_annotations.json"
    ann_path.write_text(
        json.dumps(annotations, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[annotate] Saved {len(annotations)} annotations to {ann_path}")


def cmd_correlate(args: argparse.Namespace) -> None:
    """Compute correlation between findings and bug-fixes."""
    results_dir = RESULTS_DIR
    ann_path = WORK_DIR / "bugfix_annotations.json"

    if not ann_path.exists():
        print("ERROR: Run 'annotate' first.", file=sys.stderr)
        sys.exit(1)

    annotations = json.loads(ann_path.read_text(encoding="utf-8"))

    # Group annotations by (repo, sha, window)
    ann_index: dict[tuple[str, str, int], dict[str, int]] = {}
    for ann in annotations:
        key = (ann["repo"], ann["sha"], ann["window_days"])
        ann_index[key] = ann.get("bugfix_files", {})

    # Load snapshot results
    snapshot_index: dict[tuple[str, str], dict[str, int]] = {}
    for repo_dir in sorted(results_dir.iterdir()) if results_dir.exists() else []:
        if not repo_dir.is_dir():
            continue
        for snap_file in sorted(repo_dir.glob("*.json")):
            snap = json.loads(snap_file.read_text(encoding="utf-8"))
            key = (snap["repo"], snap["sha"])
            snapshot_index[key] = snap.get("findings_per_file", {})

    # Compute correlations per (repo, window)
    correlations: list[dict[str, Any]] = []

    repos = sorted({k[0] for k in ann_index})
    for repo in repos:
        for window in BUGFIX_WINDOWS:
            # Collect matched file-level data
            finding_densities: list[float] = []
            bugfix_densities: list[float] = []
            all_finding_files: set[str] = set()
            all_bugfix_files: dict[str, int] = {}

            for (r, sha, w), bf_files in ann_index.items():
                if r != repo or w != window:
                    continue
                snap_files = snapshot_index.get((r, sha), {})

                # Merge all files from this snapshot
                all_files = set(snap_files.keys()) | set(bf_files.keys())
                for f in all_files:
                    finding_densities.append(snap_files.get(f, 0))
                    bugfix_densities.append(bf_files.get(f, 0))
                all_finding_files.update(f for f, c in snap_files.items() if c > 0)
                for f, c in bf_files.items():
                    all_bugfix_files[f] = all_bugfix_files.get(f, 0) + c

            if len(finding_densities) < 10:
                print(
                    f"[correlate] {repo} window={window}d: insufficient data ({len(finding_densities)} files)"
                )
                continue

            rho, p = _spearman_rank(finding_densities, bugfix_densities)
            rr = _relative_risk(
                all_finding_files,
                all_bugfix_files,
                set(f for i, f in enumerate(all_finding_files) if True)
                | set(all_bugfix_files.keys()),
            )

            status = "PASS" if rho >= 0.25 and p < 0.05 else "FAIL" if rho < 0.15 else "WEAK"
            correlations.append(
                {
                    "repo": repo,
                    "window_days": window,
                    "spearman_rho": round(rho, 4),
                    "p_value": round(p, 6),
                    "n_files": len(finding_densities),
                    "relative_risk": round(rr, 3),
                    "status": status,
                }
            )
            print(f"[correlate] {repo} {window}d: ρ={rho:.3f} p={p:.4f} RR={rr:.2f} → {status}")

    # Overall assessment
    pass_count = sum(1 for c in correlations if c["status"] == "PASS")
    total_repos = len(repos)

    report = {
        "version": "1.0.0",
        "created": datetime.now(UTC).isoformat(),
        "hypothesis": "H3: Drift findings correlate with subsequent bug-fix density",
        "pass_criterion": "ρ ≥ 0.25 on ≥3/5 repos",
        "overall_status": "PASS" if pass_count >= 3 else "FAIL",
        "repos_passing": pass_count,
        "repos_total": total_repos,
        "correlations": correlations,
    }

    report_path = WORK_DIR / "correlation_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"\n[correlate] Report saved to {report_path}")
    print(
        f"[correlate] Overall: {pass_count}/{total_repos} repos pass → {report['overall_status']}"
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Full pipeline: corpus → replay → annotate → correlate."""
    print("=" * 60)
    print("STAGE 1: Build corpus manifest")
    print("=" * 60)
    cmd_corpus(args)

    print("\n" + "=" * 60)
    print("STAGE 2: Replay drift analysis")
    print("=" * 60)
    cmd_replay(args)

    print("\n" + "=" * 60)
    print("STAGE 3: Annotate bug-fixes")
    print("=" * 60)
    cmd_annotate(args)

    print("\n" + "=" * 60)
    print("STAGE 4: Compute correlations")
    print("=" * 60)
    cmd_correlate(args)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Historical Replay Benchmark — correlate findings with bug-fixes"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip network operations and long-running analysis",
    )
    parser.add_argument(
        "--clone-dir",
        default=str(REPO_ROOT / ".replay-clones"),
        help="Directory for repo clones (default: .replay-clones/)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run analysis even if cached results exist",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("corpus", help="Build corpus manifest")
    subparsers.add_parser("replay", help="Run drift on snapshots")
    subparsers.add_parser("annotate", help="Annotate bug-fix commits")
    subparsers.add_parser("correlate", help="Compute correlations")
    subparsers.add_parser("run", help="Full pipeline")

    args = parser.parse_args()
    dispatch = {
        "corpus": cmd_corpus,
        "replay": cmd_replay,
        "annotate": cmd_annotate,
        "correlate": cmd_correlate,
        "run": cmd_run,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
