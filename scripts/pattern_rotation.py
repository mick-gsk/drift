#!/usr/bin/env python3
"""Pattern Rotation: auto-generate negative-pattern stubs from FP Oracle audit report.

Reads:
  oracle_fp_report.json  (from artifact download or benchmark_results/)

For each signal where FP rate exceeds threshold:
  - Checks if a recent auto-stub already exists in data/negative-patterns/patterns/
  - Creates stub .json + .py files conforming to data/negative-patterns/schema.json
  - Stubs have tp_confirmed=false so check_negative_patterns.py skips them
  - Stubs serve as human-reviewable FP tracking artifacts

Exit codes:
  0 = success (0 or more stubs created)
  1 = error (missing input, schema mismatch)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PATTERNS_DIR = REPO_ROOT / "data" / "negative-patterns" / "patterns"
SCHEMA_FILE = REPO_ROOT / "data" / "negative-patterns" / "schema.json"
REPORT_DEFAULT = REPO_ROOT / "benchmark_results" / "oracle_fp_report.json"

FP_RATE_THRESHOLD = 0.15   # 15 % FP rate triggers a stub
FP_COUNT_MIN = 2           # Minimum absolute FP count (avoids single-sample noise)
STUB_ORIGIN = "fp_oracle_auto"
STUB_ADDED_BY = "pattern_rotation_bot"


def _load_schema_required() -> set[str]:
    if not SCHEMA_FILE.exists():
        return set()
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    return set(schema.get("required", []))


def _existing_auto_stub_signals() -> set[str]:
    """Return set of signal names that already have an auto-stub."""
    result: set[str] = []
    if not PATTERNS_DIR.exists():
        return set()
    for candidate in PATTERNS_DIR.iterdir():
        if not candidate.is_dir():
            continue
        # auto stubs are named fp_oracle_{signal}_{date}
        match = re.match(r"^fp_oracle_(.+?)_\d{8}$", candidate.name)
        if match:
            result.append(match.group(1))
    return set(result)


def _valid_signal_id(sig: str) -> str:
    """Sanitize signal name to a valid identifier fragment."""
    return re.sub(r"[^a-z0-9_]", "_", sig.lower())


def _generate_stub(signal: str, fp_rate: float, fp_count: int, drift_version: str) -> Path:
    """Create a stub directory with .json + .py files.  Returns the directory path."""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    sig_id = _valid_signal_id(signal)
    stub_id = f"fp_oracle_{sig_id}_{today}"
    stub_dir = PATTERNS_DIR / stub_id
    stub_dir.mkdir(parents=True, exist_ok=True)

    # ── JSON metadata file ────────────────────────────────────────────────────
    meta = {
        "id": stub_id,
        "signal": signal,
        "origin": STUB_ORIGIN,
        "pattern_class": "fp_candidate",
        "confirmed_problematic": False,
        "severity": "low",
        "description": (
            f"Auto-generated FP tracking stub for signal '{signal}'. "
            f"FP rate in oracle audit: {fp_rate:.0%} (count={fp_count}). "
            f"Action required: extract a minimal reproducer from the oracle repository "
            f"and set tp_confirmed=true once verified."
        ),
        "tp_confirmed": False,
        "added_by": STUB_ADDED_BY,
        "drift_version": drift_version,
        "_auto_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fp_rate_at_generation": round(fp_rate, 4),
            "fp_count_at_generation": fp_count,
        },
    }
    json_path = stub_dir / f"{stub_id}.json"
    json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # ── Python stub file (required by validate_negative_patterns.py 1:1 mapping) ─
    py_path = stub_dir / f"{stub_id}.py"
    py_path.write_text(
        f"# FP oracle stub for signal: {signal}\n"
        f"# fp_rate={fp_rate:.0%}  count={fp_count}\n"
        f"# TODO: Replace with a minimal reproducer extracted from the oracle repository.\n"
        f"# Once the reproducer is confirmed, set tp_confirmed=true in {stub_id}.json.\n"
        f"pass\n",
        encoding="utf-8",
    )

    return stub_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        type=Path,
        default=REPORT_DEFAULT,
        help="Path to oracle_fp_report.json",
    )
    parser.add_argument(
        "--fp-rate-threshold",
        type=float,
        default=FP_RATE_THRESHOLD,
        help="Minimum FP rate to generate a stub (default: 0.15)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing files",
    )
    args = parser.parse_args()

    if not args.report.exists():
        print(f"[error] Report not found: {args.report}", file=sys.stderr)
        return 1

    report = json.loads(args.report.read_text(encoding="utf-8"))

    # Determine drift version for stub metadata
    drift_version = report.get("_metadata", {}).get("drift_version", "unknown")
    if drift_version == "unknown":
        try:
            import tomllib  # type: ignore[import]
            with open(REPO_ROOT / "pyproject.toml", "rb") as f:
                pyproject = tomllib.load(f)
            drift_version = pyproject.get("project", {}).get("version", "unknown")
        except Exception:  # noqa: BLE001
            pass

    # Collect aggregate FP stats per signal
    aggregate: dict[str, dict] = report.get("aggregate", {})
    if not aggregate:
        # Try to derive from repos
        for repo_data in report.get("repos", {}).values():
            for sig, stats in repo_data.get("stats_by_signal", {}).items():
                if sig not in aggregate:
                    aggregate[sig] = {"fp": 0, "tp": 0, "fp_rate": 0.0}
                aggregate[sig]["fp"] = aggregate[sig].get("fp", 0) + stats.get("fp", 0)
                aggregate[sig]["tp"] = aggregate[sig].get("tp", 0) + stats.get("tp", 0)
        for sig, vals in aggregate.items():
            total = vals["fp"] + vals["tp"]
            vals["fp_rate"] = vals["fp"] / total if total else 0.0

    existing_stubs = _existing_auto_stub_signals()

    created: list[str] = []
    skipped: list[str] = []

    for signal, stats in aggregate.items():
        fp_rate = stats.get("fp_rate") or 0.0
        fp_count = stats.get("fp", 0)

        if fp_rate < args.fp_rate_threshold or fp_count < FP_COUNT_MIN:
            continue

        sig_id = _valid_signal_id(signal)
        if sig_id in existing_stubs:
            skipped.append(signal)
            continue

        print(f"  [stub] {signal}: fp_rate={fp_rate:.0%} fp_count={fp_count}")
        if not args.dry_run:
            stub_dir = _generate_stub(signal, fp_rate, fp_count, drift_version)
            print(f"         Created: {stub_dir.relative_to(REPO_ROOT)}")
        created.append(signal)

    print(f"\nResult: {len(created)} stub(s) created, {len(skipped)} already exist.")
    if args.dry_run and created:
        print("[dry-run] No files written.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
