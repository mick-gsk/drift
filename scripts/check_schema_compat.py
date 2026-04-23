#!/usr/bin/env python3
"""JSON Schema Contract Diff Gate.

Compares the current drift.output.schema.json against a baseline (typically
from the main branch) and blocks on breaking changes.

Breaking changes detected:
  - Removal of a required field
  - Change of type/enum/const for an existing required field
  - Removal of the entire `required` array

Additive changes (new properties, new optional fields) are always allowed.

Usage:
  python scripts/check_schema_compat.py \\
    --baseline /tmp/schema_baseline.json \\
    --current drift.output.schema.json

  # Typical CI invocation:
  git show origin/main:drift.output.schema.json > /tmp/schema_baseline.json
  python scripts/check_schema_compat.py \\
    --baseline /tmp/schema_baseline.json \\
    --current drift.output.schema.json

Exit codes:
  0 – no breaking change detected
  1 – at least one breaking change found
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        print(f"ERROR: file not found: {path}", flush=True)
        sys.exit(1)
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def _field_signature(properties: dict, field: str) -> Any:
    """Return a stable signature for a property definition."""
    prop = properties.get(field, {})
    # Capture type, enum, const — the fields that define a wire contract
    return {
        k: prop[k]
        for k in ("type", "enum", "const", "$ref", "anyOf", "oneOf")
        if k in prop
    }


def find_breaking_changes(baseline: dict, current: dict) -> list[str]:
    violations: list[str] = []

    baseline_required = set(baseline.get("required", []))
    current_required = set(current.get("required", []))

    # 1. Required fields removed
    removed = baseline_required - current_required
    for field in sorted(removed):
        violations.append(f"BREAKING: required field '{field}' removed from schema")

    # 2. Type/const/enum changed for fields still required
    baseline_props = baseline.get("properties", {})
    current_props = current.get("properties", {})

    for field in sorted(baseline_required & current_required):
        old_sig = _field_signature(baseline_props, field)
        new_sig = _field_signature(current_props, field)
        if old_sig != new_sig:
            violations.append(
                f"BREAKING: field '{field}' signature changed: {old_sig!r} -> {new_sig!r}"
            )

    # 3. schema_version const specifically tracked (always a hard contract)
    baseline_ver = baseline.get("properties", {}).get("schema_version", {}).get("const")
    current_ver = current.get("properties", {}).get("schema_version", {}).get("const")
    if baseline_ver and current_ver and baseline_ver != current_ver:
        # Version bump is allowed — but only if it is additive (we already checked above).
        # Just surface it as an informational note.
        print(
            f"INFO: schema_version bumped: {baseline_ver!r} -> {current_ver!r} "
            "(ensure consumers are updated)",
            flush=True,
        )

    return violations


def main() -> None:
    parser = argparse.ArgumentParser(description="JSON Schema contract diff gate")
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline schema (e.g. from origin/main)",
    )
    parser.add_argument(
        "--current",
        default="drift.output.schema.json",
        help="Path to current schema (default: drift.output.schema.json)",
    )
    args = parser.parse_args()

    baseline = _load(args.baseline)
    current = _load(args.current)

    violations = find_breaking_changes(baseline, current)

    if violations:
        for v in violations:
            print(f"::error::{v}", flush=True)
        print(
            f"\nSchema contract broken: {len(violations)} breaking change(s) detected.",
            flush=True,
        )
        print(
            "To introduce a breaking schema change, bump the major version "
            "and update all consumers.",
            flush=True,
        )
        sys.exit(1)

    print("Schema contract: PASS — no breaking changes detected.", flush=True)


if __name__ == "__main__":
    main()
