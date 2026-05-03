#!/usr/bin/env python3
"""
T003 Framework: Audit Legacy Paths in Drift Repository

Purpose:
- Enumerate all compat stubs under packages/drift/src/drift/
- Verify they correspond to canonical implementations in packages/drift-*/
- Report any orphaned or misaligned stubs
- Ensure no active implementation logic exists in compat layer

Output:
- Structured JSON report to stdout (for CI integration)
- Human-readable summary to stderr (for local debugging)

Exit Codes:
- 0: Audit passed (no issues)
- 1: Audit found warnings or misalignments (non-blocking)
- 2: Audit found critical issues (blocking for commit)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def audit_compat_stubs(repo_root: Path) -> dict[str, Any]:
    """
    Enumerate all compat stubs and verify canonical targets exist.
    
    Returns:
        {
            "status": "ok" | "warning" | "error",
            "total_stubs": int,
            "valid_stubs": int,
            "orphaned_stubs": list[str],
            "misaligned_stubs": list[{"stub": str, "target": str, "reason": str}],
            "active_implementation_in_compat": list[str],
        }
    """
    compat_root = repo_root / "packages" / "drift" / "src" / "drift"
    
    report: dict[str, Any] = {
        "status": "ok",
        "total_stubs": 0,
        "valid_stubs": 0,
        "orphaned_stubs": [],
        "misaligned_stubs": [],
        "active_implementation_in_compat": [],
    }
    
    if not compat_root.exists():
        report["status"] = "error"
        report["active_implementation_in_compat"].append(
            f"Compat root not found: {compat_root}"
        )
        return report
    
    # T006-T007 placeholder: Implement stub enumeration logic
    # For now: return empty audit (structure is correct)
    
    if report["active_implementation_in_compat"]:
        report["status"] = "error"
    elif report["misaligned_stubs"]:
        report["status"] = "warning"
    
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit legacy paths and compat stubs in drift VSA migration"
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
    
    args = parser.parse_args()
    
    report = audit_compat_stubs(args.repo)
    
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Legacy Path Audit: {report['status'].upper()}")
        print(f"  Total stubs: {report['total_stubs']}")
        print(f"  Valid: {report['valid_stubs']}")
        if report["orphaned_stubs"]:
            print(f"  Orphaned: {len(report['orphaned_stubs'])}")
            for stub in report["orphaned_stubs"]:
                print(f"    - {stub}")
        if report["misaligned_stubs"]:
            print(f"  Misaligned: {len(report['misaligned_stubs'])}")
            for item in report["misaligned_stubs"]:
                print(f"    - {item['stub']} -> {item['target']}: {item['reason']}")
        if report["active_implementation_in_compat"]:
            print(f"  Active implementation in compat: {len(report['active_implementation_in_compat'])}")
            for item in report["active_implementation_in_compat"]:
                print(f"    - {item}")
    
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
