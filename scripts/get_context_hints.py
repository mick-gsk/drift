#!/usr/bin/env python3
"""Emit just-in-time context hints for signals found in a drift JSON report.

Called from action.yml to surface the minimal documentation slice relevant to
the signals detected in the current run. Agents can load only these files
instead of the full llms.txt, keeping context budget consumption small.

Usage::

    python scripts/get_context_hints.py <drift-results.json> [--max-hints N]

Prints one workspace-relative path per line. Exits silently (empty output)
when the report is missing, empty, or no mapped signals are found.

Exit codes:
    0 — always (errors produce empty output, never a non-zero exit)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import _context_mapping as ctx  # noqa: E402

_DEFAULT_MAX_HINTS = 12


def get_context_hints(report_path: Path, *, max_hints: int = _DEFAULT_MAX_HINTS) -> list[str]:
    """Return deduplicated context paths for the signals in *report_path*.

    Args:
        report_path: Path to a drift JSON report.
        max_hints:   Maximum number of paths to return (caps total output).

    Returns:
        List of workspace-relative ``*.md`` paths, ordered by first
        occurrence of the corresponding signal in the findings list
        (highest-scored finding first, as returned by drift).
    """
    try:
        with report_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        print(f"get_context_hints: could not read report: {exc}", file=sys.stderr)
        return []

    findings = data.get("findings", [])

    # Collect unique signal IDs preserving insertion order (highest score first).
    seen_signals: set[str] = set()
    ordered_signals: list[str] = []
    for finding in findings:
        sig = finding.get("signal", "")
        if sig and sig not in seen_signals:
            seen_signals.add(sig)
            ordered_signals.append(sig)

    # Gather context paths, deduplicating while preserving order.
    seen_paths: set[str] = set()
    hint_paths: list[str] = []
    for signal_id in ordered_signals:
        for path in ctx.signal_context_for(signal_id):
            if path not in seen_paths:
                seen_paths.add(path)
                hint_paths.append(path)

    return hint_paths[:max_hints]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("report", type=Path, help="Path to drift JSON report file.")
    parser.add_argument(
        "--max-hints",
        type=int,
        default=_DEFAULT_MAX_HINTS,
        help=f"Maximum number of context paths to emit (default: {_DEFAULT_MAX_HINTS}).",
    )
    args = parser.parse_args()

    hints = get_context_hints(args.report, max_hints=args.max_hints)
    if hints:
        print("\n".join(hints))
    return 0


if __name__ == "__main__":
    sys.exit(main())
