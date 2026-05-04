#!/usr/bin/env python3
"""Ecosystem regression gate: compare drift findings between two refs.

Usage
-----
  python scripts/ecosystem_check.py \\
      --baseline-file baseline_findings.json \\
      --pr-file pr_findings.json \\
      --repos-file benchmarks/ecosystem_repos.json \\
      --output ecosystem_report.md

The script reads two pre-generated drift JSON result files (produced by running
``drift analyze --format json --exit-zero`` against each repo at different refs),
then reports:

  - new HIGH/BLOCK findings introduced by the PR ref (regressions)
  - findings resolved by the PR ref (improvements)
  - an overall pass/fail decision (exit code 0 = pass, 1 = regressions found)

Exit codes
----------
  0  No regressions; report written to --output.
  1  One or more regressions; report written to --output.
  2  Input files missing or malformed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def _finding_key(finding: dict[str, Any]) -> str:
    """Stable key for deduplicating findings across refs."""
    return "|".join(
        [
            finding.get("signal_type", ""),
            finding.get("severity", ""),
            str(finding.get("file_path", "")),
            str(finding.get("start_line", "")),
            finding.get("rule_id", ""),
        ]
    )


def _is_regression_severity(finding: dict[str, Any]) -> bool:
    sev = finding.get("severity", "").lower()
    return sev in ("high", "block", "critical")


# ---------------------------------------------------------------------------
# Core comparison logic
# ---------------------------------------------------------------------------


def compare_findings(
    baseline: list[dict[str, Any]],
    pr_findings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (new_regressions, resolved) lists.

    Regressions = HIGH/BLOCK findings in PR but not in baseline.
    Resolved    = HIGH/BLOCK findings in baseline but not in PR.
    """
    baseline_keys = {_finding_key(f) for f in baseline if _is_regression_severity(f)}
    pr_keys = {_finding_key(f) for f in pr_findings if _is_regression_severity(f)}

    new_regression_keys = pr_keys - baseline_keys
    resolved_keys = baseline_keys - pr_keys

    new_regressions = [
        f
        for f in pr_findings
        if _is_regression_severity(f) and _finding_key(f) in new_regression_keys
    ]
    resolved = [
        f
        for f in baseline
        if _is_regression_severity(f) and _finding_key(f) in resolved_keys
    ]

    return new_regressions, resolved


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def _findings_table(findings: list[dict[str, Any]], header: str) -> list[str]:
    lines = [f"### {header}", ""]
    if not findings:
        lines.append("_None._")
        lines.append("")
        return lines

    lines.append("| Signal | Severity | File | Line | Title |")
    lines.append("|--------|----------|------|------|-------|")
    for f in findings:
        sig = f.get("signal_type", "")
        sev = f.get("severity", "")
        fp = f.get("file_path", "")
        ln = f.get("start_line", "")
        title = f.get("title", "")[:80]
        lines.append(f"| `{sig}` | {sev} | `{fp}` | {ln} | {title} |")
    lines.append("")
    return lines


def build_report(
    new_regressions: list[dict[str, Any]],
    resolved: list[dict[str, Any]],
    baseline_score: float | None,
    pr_score: float | None,
    repo_names: list[str],
) -> str:
    status = "PASS" if not new_regressions else "FAIL"
    emoji = ":white_check_mark:" if not new_regressions else ":x:"

    lines: list[str] = [
        "## Ecosystem Regression Report",
        "",
        f"**Status:** {emoji} {status}",
        "",
    ]

    if baseline_score is not None and pr_score is not None:
        delta = round(pr_score - baseline_score, 3)
        sign = "+" if delta > 0 else ""
        lines += [
            f"**Drift score:** baseline `{baseline_score}` → PR `{pr_score}` "
            f"(delta `{sign}{delta}`)",
            "",
        ]

    if repo_names:
        lines += [
            f"**Repos scanned:** {', '.join(f'`{r}`' for r in repo_names)}",
            "",
        ]

    lines += _findings_table(new_regressions, f"New regressions ({len(new_regressions)})")
    lines += _findings_table(resolved, f"Resolved findings ({len(resolved)})")

    if new_regressions:
        lines += [
            "---",
            "> **Triage:** Review each new HIGH/BLOCK finding above.",
            "> If intentional, add a path override or deferred entry in `drift.yaml`.",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ecosystem regression check for drift.")
    p.add_argument(
        "--baseline-file",
        type=Path,
        required=True,
        help="Path to drift JSON output from the baseline ref.",
    )
    p.add_argument(
        "--pr-file",
        type=Path,
        required=True,
        help="Path to drift JSON output from the PR ref.",
    )
    p.add_argument(
        "--repos-file",
        type=Path,
        default=Path("benchmarks/ecosystem_repos.json"),
        help="JSON file listing repos that were analyzed (for reporting).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=Path("ecosystem_report.md"),
        help="Path to write the markdown report.",
    )
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    baseline_data = _load_json(args.baseline_file)
    pr_data = _load_json(args.pr_file)

    baseline_findings: list[dict[str, Any]] = baseline_data.get("findings", [])
    pr_findings: list[dict[str, Any]] = pr_data.get("findings", [])
    baseline_score: float | None = baseline_data.get("drift_score")
    pr_score: float | None = pr_data.get("drift_score")

    repo_names: list[str] = []
    if args.repos_file.exists():
        repos_data = _load_json(args.repos_file)
        if isinstance(repos_data, list):
            repo_names = [r.get("name", r.get("repo", "")) for r in repos_data if isinstance(r, dict)]

    new_regressions, resolved = compare_findings(baseline_findings, pr_findings)
    report = build_report(new_regressions, resolved, baseline_score, pr_score, repo_names)

    args.output.write_text(report, encoding="utf-8")
    print(report)

    if new_regressions:
        print(
            f"\nFAIL: {len(new_regressions)} new HIGH/BLOCK finding(s) introduced.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nPASS: no regressions. {len(resolved)} finding(s) resolved.")


if __name__ == "__main__":
    main()
