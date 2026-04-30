#!/usr/bin/env python3
"""Validate the signal-level context manifest in scripts/_context_mapping.py.

Checks:
- Every path referenced in SIGNAL_CONTEXT_PATHS resolves to an existing file.
- At least MIN_MAPPED_SIGNALS signal types have a dedicated context entry.
- No single signal exceeds MAX_PATHS_PER_SIGNAL entries.
- All referenced paths are .md files (no accidental prose leaks).

Exit codes:
    0 — all checks passed
    1 — one or more validation errors

Usage::

    python scripts/validate_context_manifest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _context_mapping as ctx  # noqa: E402

# Minimum number of signals that must have a dedicated mapping.
# 24 signals are mapped at the time of introduction; 20 protects against
# accidental truncation without falsely failing on minor removals.
MIN_MAPPED_SIGNALS = 20


def _validate() -> list[str]:
    errors: list[str] = []

    mapped = ctx.SIGNAL_CONTEXT_PATHS
    if len(mapped) < MIN_MAPPED_SIGNALS:
        errors.append(
            f"SIGNAL_CONTEXT_PATHS covers only {len(mapped)} signal(s); "
            f"minimum required is {MIN_MAPPED_SIGNALS}."
        )

    for signal_id, paths in mapped.items():
        if not paths:
            errors.append(f"signal {signal_id!r}: empty context tuple.")
            continue

        if len(paths) > ctx.MAX_PATHS_PER_SIGNAL:
            errors.append(
                f"signal {signal_id!r}: {len(paths)} paths exceeds "
                f"MAX_PATHS_PER_SIGNAL={ctx.MAX_PATHS_PER_SIGNAL}."
            )

        for rel_path in paths:
            if not rel_path.endswith(".md"):
                errors.append(
                    f"signal {signal_id!r}: non-.md path: {rel_path!r}"
                )
                continue
            if " " in rel_path:
                errors.append(
                    f"signal {signal_id!r}: path contains space: {rel_path!r}"
                )
                continue
            full = _REPO_ROOT / rel_path
            if not full.is_file():
                errors.append(
                    f"signal {signal_id!r}: missing file: {rel_path}"
                )

    return errors


def main() -> int:
    errors = _validate()
    if errors:
        print("context manifest validation FAILED:", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1

    mapped = ctx.SIGNAL_CONTEXT_PATHS
    total_paths = sum(len(v) for v in mapped.values())
    print(
        f"context manifest OK: {len(mapped)} signals mapped, "
        f"{total_paths} total context paths."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
