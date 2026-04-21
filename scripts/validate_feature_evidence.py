#!/usr/bin/env python3
"""Validate a feature-evidence artifact for the pre-push gate.

Checks that a ``benchmark_results/v*_feature_evidence.json`` file:

1. Is valid JSON and contains required top-level fields.
2. Passes content-plausibility checks (metric ranges, no failing tests).
3. If a ``generated_by`` block is present — or ``--require-generated-by``
   is set — validates that the block was produced by the authorised script,
   references a real git commit, and (optionally) that the commit is an
   ancestor of the current push head.

Usage::

    python scripts/validate_feature_evidence.py path/to/evidence.json
    python scripts/validate_feature_evidence.py path/to/evidence.json \\
        --require-generated-by \\
        --push-head <SHA>

Exit codes:
    0 — evidence file is valid
    1 — validation failed (details printed to stderr)
    2 — file not found or JSON parse error
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTHORISED_SCRIPT = "scripts/generate_feature_evidence.py"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd or REPO_ROOT,
        timeout=15,
    )


def _commit_exists(sha: str) -> bool:
    """Return True if sha resolves to a commit object in the repo."""
    if not re.fullmatch(r"[0-9a-f]{4,64}", sha, re.IGNORECASE):
        return False
    result = _git("cat-file", "-e", f"{sha}^{{commit}}")
    return result.returncode == 0


def _is_ancestor(candidate_sha: str, descendant_sha: str) -> bool:
    """Return True if candidate_sha is an ancestor of descendant_sha."""
    result = _git("merge-base", "--is-ancestor", candidate_sha, descendant_sha)
    return result.returncode == 0


def _parse_timestamp(ts: str) -> datetime.datetime | None:
    """Parse ISO-8601 timestamp, return None on failure."""
    try:
        # Python 3.11+ handles Z suffix; earlier needs replace
        return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


def _check_required_fields(data: dict, issues: list[str]) -> None:
    required = ["version", "feature"]
    for field in required:
        if field not in data or not str(data[field]).strip():
            issues.append(f"Required field '{field}' is missing or empty.")


def _check_version_format(data: dict, issues: list[str]) -> None:
    version = data.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(version)):
        issues.append(
            f"'version' must be X.Y.Z semver without 'v' prefix (got: {version!r})."
        )


def _check_metric_plausibility(data: dict, issues: list[str]) -> None:
    """Check that numeric metrics are in expected ranges."""

    def _bounded(path: str, value: object) -> None:
        try:
            v = float(value)  # type: ignore[arg-type]
            if not (0.0 <= v <= 1.0):
                issues.append(f"'{path}' must be in [0, 1] (got: {v}).")
        except (TypeError, ValueError):
            issues.append(f"'{path}' is not a number (got: {value!r}).")

    # self_analysis drift_score
    if "self_analysis" in data and isinstance(data["self_analysis"], dict):
        sa = data["self_analysis"]
        if "drift_score" in sa and sa["drift_score"] is not None:
            _bounded("self_analysis.drift_score", sa["drift_score"])

    # top-level precision/recall block (optional)
    for sig_key in ("precision_recall", "precision_recall_suite"):
        if sig_key not in data or not isinstance(data[sig_key], dict):
            continue
        pr = data[sig_key]
        for metric in ("precision", "recall", "f1"):
            if metric in pr:
                _bounded(f"{sig_key}.{metric}", pr[metric])
        # Nested per-signal
        if "signals" in pr and isinstance(pr["signals"], dict):
            for sig_name, sig_data in pr["signals"].items():
                if isinstance(sig_data, dict):
                    for metric in ("precision", "recall", "f1"):
                        if metric in sig_data:
                            _bounded(f"{sig_key}.signals.{sig_name}.{metric}", sig_data[metric])

    # tests.total_failing must be 0
    if "tests" in data and isinstance(data["tests"], dict):
        failing = data["tests"].get("total_failing", 0)
        try:
            if int(failing) != 0:
                issues.append(
                    f"'tests.total_failing' must be 0 for a valid feat: push (got: {failing})."
                )
        except (TypeError, ValueError):
            issues.append(f"'tests.total_failing' is not an integer (got: {failing!r}).")


def _check_generated_by(
    data: dict,
    issues: list[str],
    *,
    require: bool,
    push_head: str | None,
) -> None:
    """Validate the generated_by block (tamper-evidence check)."""
    gb = data.get("generated_by")

    if gb is None:
        if require:
            issues.append(
                "'generated_by' block is missing. "
                f"Run `python {AUTHORISED_SCRIPT} --version ... --slug ...` "
                "to generate a machine-verified evidence file."
            )
        return  # nothing more to check

    if not isinstance(gb, dict):
        issues.append(f"'generated_by' must be a dict (got: {type(gb).__name__}).")
        return

    # Script name
    script = gb.get("script", "")
    if script != AUTHORISED_SCRIPT:
        issues.append(
            f"'generated_by.script' must be '{AUTHORISED_SCRIPT}' "
            f"(got: {script!r}). Do not manually set this field."
        )

    # git SHA must resolve to a real commit
    sha = gb.get("git_sha", "")
    if not sha or sha == "unknown":
        issues.append("'generated_by.git_sha' is missing or 'unknown'.")
    elif not _commit_exists(sha):
        issues.append(
            f"'generated_by.git_sha' ({sha!r}) does not resolve to a known commit. "
            "The evidence file may have been generated outside this repository."
        )
    elif push_head:
        # The SHA must be an ancestor of the push head — prevents reusing old SHAs
        # for a new commit's evidence.
        if not _is_ancestor(sha, push_head):
            issues.append(
                f"'generated_by.git_sha' ({sha[:12]}…) is not an ancestor of the "
                f"push head ({push_head[:12]}…). "
                "Regenerate the evidence file on the current branch."
            )

    # Timestamp sanity check
    ts_raw = gb.get("timestamp", "")
    if ts_raw:
        ts = _parse_timestamp(ts_raw)
        if ts is None:
            issues.append(
                f"'generated_by.timestamp' is not a valid ISO-8601 datetime (got: {ts_raw!r})."
            )
        else:
            now = datetime.datetime.now(datetime.timezone.utc)
            if ts > now + datetime.timedelta(minutes=5):
                issues.append(
                    f"'generated_by.timestamp' is in the future ({ts_raw!r}). "
                    "Check your system clock or regenerate the evidence file."
                )
    else:
        if require:
            issues.append("'generated_by.timestamp' is missing.")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_evidence_file(
    path: Path,
    *,
    require_generated_by: bool = False,
    push_head: str | None = None,
) -> list[str]:
    """Validate a feature-evidence JSON file.

    Args:
        path: Path to the evidence JSON file.
        require_generated_by: If True, the ``generated_by`` block is mandatory.
        push_head: Full SHA of the push head commit for ancestor checks.

    Returns:
        List of issue strings.  Empty list means the file is valid.
    """
    issues: list[str] = []

    if not path.exists():
        return [f"File not found: {path}"]

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON parse error: {exc}"]
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    _check_required_fields(data, issues)
    _check_version_format(data, issues)
    _check_metric_plausibility(data, issues)
    _check_generated_by(
        data,
        issues,
        require=require_generated_by,
        push_head=push_head,
    )

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a feature-evidence artifact for the pre-push gate.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("path", help="Path to the feature-evidence JSON file.")
    parser.add_argument(
        "--require-generated-by",
        action="store_true",
        help=(
            "Require the 'generated_by' block to be present and valid. "
            "Without this flag a file without 'generated_by' is accepted "
            "(backward-compatibility with pre-gate evidence files)."
        ),
    )
    parser.add_argument(
        "--push-head",
        metavar="SHA",
        default=None,
        help=(
            "Full SHA of the push head commit. "
            "When provided, generated_by.git_sha must be an ancestor of this commit."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    path = Path(args.path)

    issues = validate_evidence_file(
        path,
        require_generated_by=args.require_generated_by,
        push_head=args.push_head,
    )

    if issues:
        print(
            f"[validate_feature_evidence] FAIL — {path.name}",
            file=sys.stderr,
            flush=True,
        )
        for issue in issues:
            print(f"  ✗ {issue}", file=sys.stderr, flush=True)
        print(
            f"\nFix: regenerate via `python {AUTHORISED_SCRIPT} --version ... --slug ...`",
            file=sys.stderr,
            flush=True,
        )
        return 1

    print(
        f"[validate_feature_evidence] OK — {path.name}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
