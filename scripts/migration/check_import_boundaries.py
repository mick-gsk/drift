#!/usr/bin/env python3
"""
T004 Framework: Check Import Boundaries for VSA Packages

Purpose:
- Verify that canonical package paths (drift_engine, drift_cli, drift_config, etc.)
  are NOT imported directly in public APIs
- Enforce the rule: External code uses drift.* compat paths, internal code uses drift_*.
- Detect backdoor imports (canonical package in top-level imports)

Output:
- Structured JSON report to stdout (for CI integration)
- Human-readable summary to stderr (for local debugging)

Exit Codes:
- 0: Boundary check passed (no violations)
- 1: Check found warnings (non-blocking)
- 2: Check found critical violations (blocking for commit)
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any


def check_import_boundaries(repo_root: Path) -> dict[str, Any]:
    """
    Scan public API entry points and check for direct canonical package imports.
    
    Returns:
        {
            "status": "ok" | "warning" | "error",
            "files_scanned": int,
            "violations": list[{"file": str, "line": int, "import": str, "reason": str}],
        }
    """
    compat_root = repo_root / "packages" / "drift" / "src" / "drift"
    
    report: dict[str, Any] = {
        "status": "ok",
        "files_scanned": 0,
        "violations": [],
    }
    
    if not compat_root.exists():
        report["status"] = "error"
        report["violations"].append(
            {
                "file": str(compat_root),
                "line": 0,
                "import": "N/A",
                "reason": "Compat root not found",
            }
        )
        return report
    
    # T007-T009 placeholder: Implement boundary check logic
    # For now: return empty check (structure is correct)
    
    if report["violations"]:
        report["status"] = "error"
    
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check import boundaries for VSA canonical packages"
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Path to drift repository root (default: cwd)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON report (default: human-readable)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code 2 if any warnings found (strict mode)",
    )
    parser.add_argument(
        "--package",
        action="append",
        help="Check specific package (can be repeated; default: all)",
    )
    
    args = parser.parse_args()
    
    report = check_import_boundaries(args.repo)
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Import Boundary Check: {report['status'].upper()}")
        print(f"  Files scanned: {report['files_scanned']}")
        if report["violations"]:
            print(f"  Violations: {len(report['violations'])}")
            for v in report["violations"]:
                print(f"    - {v['file']}:{v['line']}: {v['import']}")
                print(f"      {v['reason']}")
    
    # Determine exit code
    exit_code = {
        "ok": 0,
        "warning": 1,
        "error": 2,
    }.get(report["status"], 2)
    
    if args.strict and exit_code == 1:
        exit_code = 2
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
