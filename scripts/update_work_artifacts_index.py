#!/usr/bin/env python3
"""Generate work_artifacts/index.json — machine-readable index of work_artifacts/.

An agent resuming after a session handover can read this index instead of
scanning the entire work_artifacts/ tree.  Each entry carries the artifact
type (inferred from name conventions), creation time (mtime), and path
relative to the repository root.

Usage::

    python scripts/update_work_artifacts_index.py

The file work_artifacts/index.json is written (or overwritten) atomically.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORK_ARTIFACTS_DIR = REPO_ROOT / "work_artifacts"
INDEX_PATH = WORK_ARTIFACTS_DIR / "index.json"

# Type-inference rules: matched in order, first match wins.
_TYPE_RULES: list[tuple[str, str]] = [
    # Session / handover
    ("session_", "session-handover"),
    # Audits and engineering investigations
    ("context_engineering_", "context-engineering-audit"),
    ("harness_engine_", "harness-engine-audit"),
    ("actionability_review_", "actionability-review"),
    ("role_based_review_", "role-based-review"),
    ("shareability_review_", "shareability-review"),
    ("pre_push_review_", "pre-push-review"),
    # Drift run outputs
    ("drift_fix_plan_", "fix-plan"),
    ("drift_scan_", "scan-result"),
    ("drift_analyze_", "analysis-result"),
    ("drift_brief", "brief-result"),
    ("drift_diff_", "diff-result"),
    ("drift_baseline_", "baseline-snapshot"),
    ("drift_latest_run", "analysis-result"),
    ("drift_scope_", "scope-analysis"),
    ("drift_self_", "self-analysis"),
    ("drift_validate", "validation-result"),
    ("latest_drift_", "analysis-result"),
    ("current_score", "score-snapshot"),
    ("current_src", "scan-result"),
    ("mds_live", "scan-result"),
    # MCP diagnostics
    ("mcp_perf_", "mcp-perf-benchmark"),
    ("mcp_schema_", "mcp-schema-snapshot"),
    ("mcp_probe_", "probe-script"),
    ("mcp_server_", "mcp-server-log"),
    ("mcp_stdio_", "mcp-server-log"),
    ("mcp_allowtty_", "mcp-server-log"),
    ("mcp_min_client", "probe-script"),
    # Evidence and benchmarks
    ("quality_loop_evidence_", "quality-loop-evidence"),
    ("repro_bundle", "repro-bundle"),
    ("epoch_b_", "epoch-benchmark"),
    ("benchmark_", "benchmark-result"),
    ("mutation_benchmark", "benchmark-result"),
    # Findings-reduction work
    ("reduce_findings_", "reduce-findings"),
    ("fp_reduction_", "fp-reduction"),
    ("first_run_dropoffs_", "first-run-dropoffs"),
    ("signal_quality_", "signal-quality"),
    # Reports and analyses
    ("blast_report", "blast-report"),
    ("strategy_", "strategy-analysis"),
    ("d2c_", "d2c-analysis"),
    ("mirror_study", "study"),
    ("brief_study", "study"),
    ("internal_eval", "evaluation"),
    # Community / outreach
    ("community-pitch", "community-outreach"),
    ("good-first-issues", "community-outreach"),
    ("hn-author-comment", "community-outreach"),
    ("reddit_", "community-outreach"),
    ("devto-", "community-outreach"),
    # Competitive / strategy
    ("competitive_", "competitive-analysis"),
    ("trending_", "market-research"),
    ("roi_", "roi-analysis"),
    # Release artifacts
    ("v2.", "release-evidence"),
    # Issue analysis
    ("issue_", "issue-analysis"),
    # Validation
    ("validation", "validation-result"),
    # Diagnostics / temp
    ("dia_", "diagnostic"),
    ("score_no_", "score-snapshot"),
    ("tmp_", "temp-artifact"),
    ("_tmp_", "temp-artifact"),
    ("_current_", "temp-artifact"),
    ("_post_", "temp-artifact"),
    ("_pre_", "temp-artifact"),
    ("_realfix_", "temp-artifact"),
    # Drift agent test sessions / manual runs (no trailing underscore)
    ("drift_fix_plan.", "fix-plan"),
    ("drift_agent_test_", "session-handover"),
    # VSA / architecture studies
    ("vsa_", "architecture-study"),
    # Test / SARIF outputs
    ("test_sarif", "test-output"),
    ("test_no_", "test-output"),
    ("test_select_", "test-output"),
    # External tool outputs
    ("aicoach_", "external-tool-output"),
    ("out.", "external-tool-output"),
    # Launch / film / media artifacts
    ("launch_film_", "media-artifact"),
    # GitHub / repo analyses
    ("github_repo_", "repo-analysis"),
    ("adoption_analysis_", "repo-analysis"),
    ("src_drift_", "scan-result"),
    # Strategy docs without timestamp
    ("strategiepapier_", "strategy-analysis"),
    # Trailer / creative
    ("trailer-script", "media-artifact"),
    # Strict audit outputs
    ("v261_strict_", "audit-result"),
]

_EXT_TYPE_MAP: dict[str, str] = {
    ".json": "json-artifact",
    ".md": "markdown-artifact",
    ".txt": "log-artifact",
    ".log": "log-artifact",
    ".py": "probe-script",
    ".html": "report-artifact",
    ".jsonl": "log-artifact",
}


def _infer_type(name: str) -> str:
    lower = name.lower()
    for prefix, artifact_type in _TYPE_RULES:
        if lower.startswith(prefix):
            return artifact_type
    # Fall back to extension-based classification
    suffix = Path(name).suffix.lower()
    if suffix in _EXT_TYPE_MAP:
        return _EXT_TYPE_MAP[suffix]
    return "misc-artifact"


def _mtime_iso(path: Path) -> str:
    mtime = path.stat().st_mtime
    return (
        dt.datetime.fromtimestamp(mtime, tz=dt.UTC)
        .replace(microsecond=0)
        .isoformat()
    )


def build_index() -> dict:  # type: ignore[type-arg]
    """Scan work_artifacts/ and return the index payload."""
    entries = []
    if not WORK_ARTIFACTS_DIR.exists():
        return {
            "generated_at": _utc_now_iso(),
            "work_artifacts_dir": "work_artifacts",
            "entries": [],
        }

    for child in sorted(WORK_ARTIFACTS_DIR.iterdir()):
        if child.name.startswith(".") or child.name == "index.json":
            continue
        rel = child.relative_to(REPO_ROOT).as_posix()
        entries.append(
            {
                "path": rel,
                "type": _infer_type(child.name),
                "created_at": _mtime_iso(child),
                "is_dir": child.is_dir(),
            }
        )

    return {
        "generated_at": _utc_now_iso(),
        "work_artifacts_dir": "work_artifacts",
        "entries": entries,
    }


def _utc_now_iso() -> str:
    return (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
    )


def write_index(payload: dict) -> None:  # type: ignore[type-arg]
    """Write payload to work_artifacts/index.json atomically (via temp file)."""
    WORK_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = INDEX_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp_path, INDEX_PATH)


def main() -> None:
    payload = build_index()
    write_index(payload)
    n = len(payload["entries"])
    print(f"work_artifacts/index.json written ({n} entries).")


if __name__ == "__main__":
    main()
