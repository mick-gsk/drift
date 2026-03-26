#!/usr/bin/env python3
"""Repair Benchmark for drift agent-tasks.

Validates that drift's agent-tasks produce structurally valid, correctly
prioritized repair tasks with verifiable success criteria, and that
applying correct repairs measurably reduces drift scores while incorrect
repairs are rejected.

Phases:
  A — Controlled repairs on synthetic repos modeled after flask/httpx data
  B — Task quality validation against existing flask/httpx _full.json

Usage:
    python scripts/repair_benchmark.py            # run + print summary
    python scripts/repair_benchmark.py --json      # run + save results

Output (--json):
    benchmark_results/repair/summary.json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from drift import __version__
from drift.analyzer import analyze_repo
from drift.models import Finding, RepoAnalysis, Severity, SignalType
from drift.output.agent_tasks import analysis_to_agent_tasks_json
from drift.output.json_output import analysis_to_json

# Import repo builders (same directory)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _repair_repos import (  # noqa: E402
    create_datalib,
    create_webapp,
    repair_datalib_eds_correct,
    repair_datalib_mds_correct,
    repair_webapp_mds_correct,
    repair_webapp_mds_incorrect,
)

OUT_DIR = Path(__file__).resolve().parent.parent / "benchmark_results" / "repair"
BENCH_DIR = Path(__file__).resolve().parent.parent / "benchmark_results"

# =========================================================================
# Helpers
# =========================================================================


def _init_git(d: Path) -> None:
    subprocess.run(["git", "init"], cwd=d, capture_output=True)
    subprocess.run(["git", "config", "user.email", "bench@drift.dev"], cwd=d, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Drift Bench"], cwd=d, capture_output=True)
    subprocess.run(["git", "add", "."], cwd=d, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=d, capture_output=True)


def _commit(d: Path, msg: str) -> None:
    subprocess.run(["git", "add", "."], cwd=d, capture_output=True)
    subprocess.run(["git", "commit", "-m", msg, "--allow-empty"], cwd=d, capture_output=True)


def _analyze(d: Path) -> dict:
    return json.loads(analysis_to_json(analyze_repo(d, since_days=90)))


def _agent_tasks(d: Path) -> dict:
    return json.loads(analysis_to_agent_tasks_json(analyze_repo(d, since_days=90)))


def _sig_count(a: dict, sig: str) -> int:
    return sum(1 for f in a.get("findings", []) if f["signal"] == sig)


def _find(a: dict, sig: str, kw: str) -> dict | None:
    for f in a.get("findings", []):
        if f["signal"] == sig and kw.lower() in f.get("title", "").lower():
            return f
    return None


def _git_diff_stats(d: Path) -> dict:
    """Return diff stats for the last commit (files changed, insertions, deletions)."""
    r = subprocess.run(
        ["git", "diff", "--shortstat", "HEAD~1", "HEAD"],
        cwd=d,
        capture_output=True,
        text=True,
    )
    line = r.stdout.strip()
    files = int(m.group(1)) if (m := re.search(r"(\d+) file", line)) else 0
    ins = int(m.group(1)) if (m := re.search(r"(\d+) insertion", line)) else 0
    dels = int(m.group(1)) if (m := re.search(r"(\d+) deletion", line)) else 0
    return {
        "files_changed": files,
        "insertions": ins,
        "deletions": dels,
        "total_diff_lines": ins + dels,
    }


def _per_signal_breakdown(analysis: dict) -> dict:
    """Group findings by signal with count and total score."""
    by_sig: dict[str, dict] = {}
    for f in analysis.get("findings", []):
        sig = f["signal"]
        if sig not in by_sig:
            by_sig[sig] = {"count": 0, "total_score": 0.0, "severities": []}
        by_sig[sig]["count"] += 1
        by_sig[sig]["total_score"] = round(by_sig[sig]["total_score"] + f.get("score", 0), 4)
        by_sig[sig]["severities"].append(f.get("severity", "unknown"))
    return by_sig


def _task_complexity_distribution(tasks: dict) -> dict:
    """Return complexity distribution + median from agent-task output."""
    complexities = [t.get("complexity", "unknown") for t in tasks.get("tasks", [])]
    dist: dict[str, int] = {}
    for c in complexities:
        dist[c] = dist.get(c, 0) + 1
    return {"distribution": dist, "total_tasks": len(complexities)}


def _check_determinism(d: Path, *, runs: int = 3) -> dict:
    """Run analysis N times on the same repo state, verify identical output."""
    scores: list[float] = []
    finding_counts: list[int] = []
    task_counts: list[int] = []
    for _ in range(runs):
        a = _analyze(d)
        t = _agent_tasks(d)
        scores.append(a["drift_score"])
        finding_counts.append(len(a["findings"]))
        task_counts.append(t["task_count"])
    identical = (
        len(set(scores)) == 1 and len(set(finding_counts)) == 1 and len(set(task_counts)) == 1
    )
    return {
        "runs": runs,
        "identical": identical,
        "scores": scores,
        "finding_counts": finding_counts,
        "task_counts": task_counts,
    }


def _score_delta_per_signal(baseline: dict, post: dict) -> dict:
    """Compute per-signal score deltas between baseline and post-repair."""
    bl_sigs = _per_signal_breakdown(baseline)
    post_sigs = _per_signal_breakdown(post)
    deltas: dict = {}
    for sig in set(list(bl_sigs.keys()) + list(post_sigs.keys())):
        bl_s = bl_sigs.get(sig, {"count": 0, "total_score": 0.0})
        po_s = post_sigs.get(sig, {"count": 0, "total_score": 0.0})
        deltas[sig] = {
            "baseline_count": bl_s["count"],
            "post_count": po_s["count"],
            "count_delta": po_s["count"] - bl_s["count"],
            "baseline_score": bl_s["total_score"],
            "post_score": po_s["total_score"],
            "score_delta": round(po_s["total_score"] - bl_s["total_score"], 4),
        }
    return deltas


def _print_diff(repair_result: dict) -> None:
    ds = repair_result["diff_stats"]
    print(f"    Diff: {ds['files_changed']} files, "
          f"{ds['total_diff_lines']} lines")


def _print_determinism(det: dict) -> None:
    tag = "PASS" if det["identical"] else "FAIL"
    print(f"  Determinism ({det['runs']} runs): {tag}")


# =========================================================================
# Task quality validation
# =========================================================================

_TOP_KEYS = {
    "version",
    "schema",
    "repo",
    "analyzed_at",
    "drift_score",
    "severity",
    "task_count",
    "tasks",
}
_TASK_KEYS = {
    "id",
    "signal_type",
    "severity",
    "priority",
    "title",
    "description",
    "action",
    "complexity",
    "expected_effect",
    "success_criteria",
    "depends_on",
    "metadata",
}
_PREFIXES = {
    "pfs",
    "avs",
    "mds",
    "eds",
    "tvs",
    "sms",
    "doc",
    "bro",
    "tes",
    "gua",
    "nam",
    "byp",
    "exc",
}


def _validate_quality(td: dict) -> dict:
    r: dict = {
        "schema_valid": True,
        "priorities_sequential": True,
        "all_have_criteria": True,
        "all_have_action": True,
        "all_have_effect": True,
        "ids_unique": True,
        "ids_prefixed": True,
        "details": [],
    }
    for k in _TOP_KEYS:
        if k not in td:
            r["schema_valid"] = False
            r["details"].append(f"Missing top key: {k}")

    tasks = td.get("tasks", [])
    if td.get("task_count") != len(tasks):
        r["schema_valid"] = False

    seen: set[str] = set()
    prev = 0
    for t in tasks:
        tid = t.get("id", "?")
        for fld in _TASK_KEYS:
            if fld not in t:
                r["schema_valid"] = False
                r["details"].append(f"{tid} missing {fld}")
        if tid in seen:
            r["ids_unique"] = False
        seen.add(tid)
        pfx = tid.split("-")[0] if "-" in tid else ""
        if pfx not in _PREFIXES:
            r["ids_prefixed"] = False
        prio = t.get("priority", 0)
        if prio != prev + 1:
            r["priorities_sequential"] = False
        prev = prio
        if not t.get("success_criteria"):
            r["all_have_criteria"] = False
        if not t.get("action"):
            r["all_have_action"] = False
        if not t.get("expected_effect"):
            r["all_have_effect"] = False

    bools = [
        r["schema_valid"],
        r["priorities_sequential"],
        r["all_have_criteria"],
        r["all_have_action"],
        r["all_have_effect"],
        r["ids_unique"],
        r["ids_prefixed"],
    ]
    r["quality_score"] = sum(bools) / len(bools)
    r["task_count"] = len(tasks)
    return r


# =========================================================================
# Repair step
# =========================================================================


def _repair_step(d, *, fn, msg, sig, kw, baseline, correct, fail_text=""):
    desc = fn(d)
    _commit(d, msg)
    post = _analyze(d)
    bc, pc = _sig_count(baseline, sig), _sig_count(post, sig)
    bf, pf = _find(baseline, sig, kw), _find(post, sig, kw)
    gone = bf is not None and pf is None
    ok = (gone or pc < bc) if correct else (not gone and pc >= bc)
    diff = _git_diff_stats(d)
    sig_deltas = _score_delta_per_signal(baseline, post)
    res = {
        "signal": sig,
        "repair_type": "correct" if correct else "incorrect",
        "repair_description": desc,
        "baseline_drift_score": baseline["drift_score"],
        "post_repair_drift_score": post["drift_score"],
        "drift_score_delta": round(post["drift_score"] - baseline["drift_score"], 4),
        "baseline_signal_findings": bc,
        "post_repair_signal_findings": pc,
        "finding_resolved": gone,
        "verification": "PASS" if ok else "FAIL",
        "diff_stats": diff,
        "per_signal_deltas": sig_deltas,
    }
    if fail_text:
        res["failure_analysis"] = fail_text
    return res


# =========================================================================
# Phase B: real data validation
# =========================================================================


def _validate_real() -> dict:
    out: dict = {}
    for name in ("flask", "httpx"):
        fp = BENCH_DIR / f"{name}_full.json"
        if not fp.exists():
            out[name] = {"error": f"{fp.name} not found"}
            continue
        raw = json.loads(fp.read_text(encoding="utf-8"))
        findings: list[Finding] = []
        for f in raw.get("findings", []):
            try:
                findings.append(
                    Finding(
                        signal_type=SignalType(f["signal"]),
                        severity=Severity(f["severity"]),
                        score=f["score"],
                        title=f["title"],
                        description=f.get("description", ""),
                        file_path=Path(f["file"]) if f.get("file") else None,
                        start_line=f.get("start_line"),
                        end_line=f.get("end_line"),
                        related_files=[Path(r) for r in f.get("related_files", [])],
                        fix=f.get("fix"),
                        impact=f.get("impact", 0.0),
                        metadata=f.get("metadata", {}),
                    )
                )
            except (ValueError, KeyError):
                continue
        analysis = RepoAnalysis(
            repo_path=Path(raw.get("repo", f"/bench/{name}")),
            analyzed_at=datetime.now(UTC),
            drift_score=raw.get("drift_score", 0),
            findings=findings,
        )
        td = json.loads(analysis_to_agent_tasks_json(analysis))
        q = _validate_quality(td)
        out[name] = {
            "source_findings": len(findings),
            "generated_tasks": td["task_count"],
            "conversion_rate": round(td["task_count"] / len(findings), 3) if findings else 0,
            "quality": q,
            "top_3_tasks": [
                {
                    "id": t["id"],
                    "signal": t["signal_type"],
                    "title": t["title"],
                    "criteria_count": len(t["success_criteria"]),
                }
                for t in td["tasks"][:3]
            ],
        }
    return out


# =========================================================================
# Main
# =========================================================================


def run_benchmark() -> dict:
    results: dict = {
        "_metadata": {
            "drift_version": __version__,
            "generated_at": datetime.now(UTC).isoformat(),
            "methodology": "synthetic_controlled_repair",
            "description": (
                "Validates agent-tasks correctness, repair causality, "
                "and verification sharpness using synthetic repos modeled "
                "after flask and httpx benchmark data."
            ),
        },
        "repos": {},
        "real_data_validation": {},
        "summary": {},
    }

    # ---- Phase A-1: webapp ----
    print("=" * 60)
    print("Phase A-1: webapp (Flask-like patterns)")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="drift_repair_webapp_") as tmp:
        d = Path(tmp)
        muts = create_webapp(d)
        _init_git(d)
        print(f"  Injected: {sum(len(v) for v in muts.values())} issues")

        bl = _analyze(d)
        bt = _agent_tasks(d)
        print(
            f"  Baseline: score={bl['drift_score']:.3f}, "
            f"findings={len(bl['findings'])}, tasks={bt['task_count']}"
        )
        tq = _validate_quality(bt)
        print(f"  Task quality: {tq['quality_score']:.2f}")

        sig_breakdown = _per_signal_breakdown(bl)
        complexity_dist = _task_complexity_distribution(bt)
        determinism = _check_determinism(d)
        _print_determinism(determinism)

        # Correct MDS repair
        print("\n  [CORRECT] MDS: consolidate _make_timedelta")
        r1 = _repair_step(
            d,
            fn=repair_webapp_mds_correct,
            msg="Fix: consolidate _make_timedelta",
            sig="mutant_duplicate",
            kw="make_timedelta",
            baseline=bl,
            correct=True,
        )
        print(
            f"  {r1['baseline_signal_findings']} -> {r1['post_repair_signal_findings']} "
            f"(delta={r1['drift_score_delta']:+.3f}) [{r1['verification']}]"
        )
        _print_diff(r1)

        # Restore baseline for failure case
        shutil.rmtree(d / "src")
        shutil.rmtree(d / "tests")
        (d / "README.md").unlink(missing_ok=True)
        create_webapp(d)
        _commit(d, "Restore baseline")
        bl2 = _analyze(d)

        # Incorrect MDS repair
        print("\n  [INCORRECT] MDS: rename without consolidation (failure case)")
        r2 = _repair_step(
            d,
            fn=repair_webapp_mds_incorrect,
            msg="Attempted fix: rename (incorrect)",
            sig="mutant_duplicate",
            kw="timedelta",
            baseline=bl2,
            correct=False,
            fail_text=(
                "Renaming a function does not resolve MDS. Drift uses body "
                "hashes, not names. Identical body still triggers detection."
            ),
        )
        print(
            f"  {r2['baseline_signal_findings']} -> {r2['post_repair_signal_findings']} "
            f"(delta={r2['drift_score_delta']:+.3f}) [{r2['verification']}]"
        )
        _print_diff(r2)

        results["repos"]["webapp"] = {
            "description": "Flask-like web app with MDS + PFS patterns",
            "mutations": muts,
            "baseline": {
                "drift_score": bl["drift_score"],
                "findings_count": len(bl["findings"]),
                "task_count": bt["task_count"],
                "signal_breakdown": sig_breakdown,
            },
            "task_quality": tq,
            "task_complexity": complexity_dist,
            "determinism": determinism,
            "repairs": [r1],
            "failure_cases": [r2],
        }

    # ---- Phase A-2: datalib ----
    print("\n" + "=" * 60)
    print("Phase A-2: datalib (httpx-like patterns)")
    print("=" * 60)

    with tempfile.TemporaryDirectory(prefix="drift_repair_datalib_") as tmp:
        d = Path(tmp)
        muts = create_datalib(d)
        _init_git(d)
        print(f"  Injected: {sum(len(v) for v in muts.values())} issues")

        bl = _analyze(d)
        bt = _agent_tasks(d)
        print(
            f"  Baseline: score={bl['drift_score']:.3f}, "
            f"findings={len(bl['findings'])}, tasks={bt['task_count']}"
        )
        tq = _validate_quality(bt)
        print(f"  Task quality: {tq['quality_score']:.2f}")

        sig_breakdown_dl = _per_signal_breakdown(bl)
        complexity_dist_dl = _task_complexity_distribution(bt)
        determinism_dl = _check_determinism(d)
        _print_determinism(determinism_dl)

        # Correct MDS repair
        print("\n  [CORRECT] MDS: BaseDecoder extraction")
        r3 = _repair_step(
            d,
            fn=repair_datalib_mds_correct,
            msg="Fix: BaseDecoder extraction",
            sig="mutant_duplicate",
            kw="flush",
            baseline=bl,
            correct=True,
        )
        print(
            f"  {r3['baseline_signal_findings']} -> {r3['post_repair_signal_findings']} "
            f"(delta={r3['drift_score_delta']:+.3f}) [{r3['verification']}]"
        )
        _print_diff(r3)

        # Correct EDS repair (sequential)
        post_mds = _analyze(d)
        print("\n  [CORRECT] EDS: docstrings + function split")
        r4 = _repair_step(
            d,
            fn=repair_datalib_eds_correct,
            msg="Fix: docstrings + split",
            sig="explainability_deficit",
            kw="transform",
            baseline=post_mds,
            correct=True,
        )
        print(
            f"  {r4['baseline_signal_findings']} -> {r4['post_repair_signal_findings']} "
            f"(delta={r4['drift_score_delta']:+.3f}) [{r4['verification']}]"
        )
        _print_diff(r4)

        results["repos"]["datalib"] = {
            "description": "httpx-like data lib with MDS + EDS + SMS patterns",
            "mutations": muts,
            "baseline": {
                "drift_score": bl["drift_score"],
                "findings_count": len(bl["findings"]),
                "task_count": bt["task_count"],
                "signal_breakdown": sig_breakdown_dl,
            },
            "task_quality": tq,
            "task_complexity": complexity_dist_dl,
            "determinism": determinism_dl,
            "repairs": [r3, r4],
            "failure_cases": [],
        }

    # ---- Phase B: real data ----
    print("\n" + "=" * 60)
    print("Phase B: Real data validation (flask, httpx)")
    print("=" * 60)

    rv = _validate_real()
    results["real_data_validation"] = rv
    for name, data in rv.items():
        if "error" in data:
            print(f"  {name}: {data['error']}")
        else:
            print(
                f"  {name}: {data['source_findings']} findings -> "
                f"{data['generated_tasks']} tasks "
                f"(rate={data['conversion_rate']:.0%}, "
                f"quality={data['quality']['quality_score']:.2f})"
            )

    # ---- Summary ----
    tr = sum(len(r["repairs"]) for r in results["repos"].values())
    pr = sum(
        sum(1 for x in r["repairs"] if x["verification"] == "PASS")
        for r in results["repos"].values()
    )
    tf = sum(len(r["failure_cases"]) for r in results["repos"].values())
    df = sum(
        sum(1 for x in r["failure_cases"] if x["verification"] == "PASS")
        for r in results["repos"].values()
    )
    # FAR/FRR: explicit verification metrics
    # FAR = fraction of incorrect repairs accepted as correct (should be 0)
    # FRR = fraction of correct repairs rejected as failed (should be 0)
    false_accepts = sum(
        sum(1 for x in r["failure_cases"] if x["verification"] == "FAIL")
        for r in results["repos"].values()
    )
    false_rejects = sum(
        sum(1 for x in r["repairs"] if x["verification"] == "FAIL")
        for r in results["repos"].values()
    )

    # Per-signal coverage: which signals had repairs attempted + verified
    signal_coverage: dict = {}
    for repo in results["repos"].values():
        for x in repo["repairs"] + repo.get("failure_cases", []):
            sig = x["signal"]
            if sig not in signal_coverage:
                signal_coverage[sig] = {
                    "correct_attempted": 0,
                    "correct_passed": 0,
                    "incorrect_attempted": 0,
                    "incorrect_detected": 0,
                }
            if x["repair_type"] == "correct":
                signal_coverage[sig]["correct_attempted"] += 1
                if x["verification"] == "PASS":
                    signal_coverage[sig]["correct_passed"] += 1
            else:
                signal_coverage[sig]["incorrect_attempted"] += 1
                if x["verification"] == "PASS":
                    signal_coverage[sig]["incorrect_detected"] += 1

    # Determinism across repos
    det_all = all(
        r.get("determinism", {}).get("identical", False) for r in results["repos"].values()
    )

    # Median diff size across repairs
    all_diffs = [
        x.get("diff_stats", {}).get("total_diff_lines", 0)
        for repo in results["repos"].values()
        for x in repo["repairs"]
    ]
    median_diff = sorted(all_diffs)[len(all_diffs) // 2] if all_diffs else 0

    results["summary"] = {
        "total_repos": len(results["repos"]),
        "total_repairs_attempted": tr,
        "repairs_verified": pr,
        "repair_success_rate": pr / tr if tr else 0,
        "total_failure_cases": tf,
        "failures_correctly_detected": df,
        "verification_metrics": {
            "false_acceptance_rate": round(false_accepts / tf, 3) if tf else 0,
            "false_rejection_rate": round(false_rejects / tr, 3) if tr else 0,
            "true_positive_rate": round(pr / tr, 3) if tr else 0,
            "true_negative_rate": round(df / tf, 3) if tf else 0,
        },
        "signal_coverage": signal_coverage,
        "determinism": {
            "all_repos_deterministic": det_all,
            "runs_per_repo": 3,
        },
        "effort_metrics": {
            "median_diff_lines": median_diff,
            "all_diff_lines": all_diffs,
        },
        "real_data_repos_validated": len([v for v in rv.values() if "error" not in v]),
        "claim_boundary": {
            "proven": [
                "Deterministic repair-task generation from analysis findings",
                "Controlled verification: correct repairs reduce drift scores",
                "Rejection sharpness: incorrect repairs are not falsely accepted",
                "Task schema completeness and priority ordering",
                "Reproducibility: identical input produces identical output",
            ],
            "not_yet_proven": [
                "Real coding agents executing tasks autonomously in production repos",
                "Multi-step repair orchestration across dependent findings",
                "Comparative advantage over unguided agent repair",
                "Broad signal coverage (only MDS/EDS verified, 4 signals untested)",
            ],
        },
        "conclusion": (
            "Translation + Verification benchmark: agent-tasks produce valid, "
            "correctly prioritized repair tasks. Correct repairs measurably "
            "reduce drift scores. Incorrect repairs are rejected. "
            "Deterministic across repeated runs."
            if pr == tr and df == tf and det_all
            else "Some results did not verify as expected — see details."
        ),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    s = results["summary"]
    vm = s["verification_metrics"]
    print(f"  Repos tested:            {s['total_repos']}")
    print(f"  Repairs verified:        {pr}/{tr}")
    print(f"  Failure cases detected:  {df}/{tf}")
    print(f"  Repair success rate:     {s['repair_success_rate']:.0%}")
    print(f"  False acceptance rate:   {vm['false_acceptance_rate']:.0%}")
    print(f"  False rejection rate:    {vm['false_rejection_rate']:.0%}")
    print(f"  Deterministic:           {'YES' if det_all else 'NO'}")
    print(f"  Median diff size:        {median_diff} lines")
    print(f"  Signals covered:         {', '.join(signal_coverage.keys())}")
    print(f"  Real data validated:     {s['real_data_repos_validated']} repos")

    return results


def main():
    parser = argparse.ArgumentParser(description="Drift Repair Benchmark")
    parser.add_argument(
        "--json", action="store_true", help="Save results to benchmark_results/repair/"
    )
    args = parser.parse_args()

    results = run_benchmark()

    if args.json:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "summary.json").write_text(
            json.dumps(results, indent=2, default=str), encoding="utf-8"
        )
        print(f"\nSaved to {OUT_DIR / 'summary.json'}")
    else:
        print("\nRun with --json to save results.")


if __name__ == "__main__":
    main()
