#!/usr/bin/env python3
"""Signal Coverage Matrix — tracks signal availability across drift releases.

Extracts signal inventory from git-tagged versions by reading the
``src/drift/signals/`` directory at each tag.  Produces a JSON artefact
suitable for badges, STUDY.md tables, and cross-version comparison.

Usage:
    python scripts/signal_coverage_matrix.py [--output FILE]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

# Milestone versions to probe (manually curated — keeps output concise).
# Extend when new signal batches ship.
MILESTONES: list[str] = [
    "v0.5.0",   # initial 6-signal baseline
    "v0.7.0",   # +NBV, BAT, ECM, TSA
    "v0.8.0",   # +CCC, COD
    "v0.10.0",  # +CIR, CXS, FOE, DCA
    "v1.1.11",  # +MAZ, HSC, ISD (security)
    "v2.1.0",   # current
]

# Canonical abbreviation map (source of truth: api_helpers.py).
# File-stem → abbreviation.
STEM_TO_ABBREV: dict[str, str] = {
    "pattern_fragmentation": "PFS",
    "architecture_violation": "AVS",
    "mutant_duplicates": "MDS",
    "temporal_volatility": "TVS",
    "explainability_deficit": "EDS",
    "system_misalignment": "SMS",
    "doc_impl_drift": "DIA",
    "broad_exception_monoculture": "BEM",
    "test_polarity_deficit": "TPD",
    "guard_clause_deficit": "GCD",
    "naming_contract_violation": "NBV",
    "bypass_accumulation": "BAT",
    "exception_contract_drift": "ECM",
    "cohesion_deficit": "COD",
    "co_change_coupling": "CCC",
    "ts_architecture": "TSA",
    "cognitive_complexity": "CXS",
    "fan_out_explosion": "FOE",
    "circular_import": "CIR",
    "dead_code_accumulation": "DCA",
    "missing_authorization": "MAZ",
    "insecure_default": "ISD",
    "hardcoded_secret": "HSC",  # pragma: allowlist secret
}

# Ordered for display (roughly by introduction date).
SIGNAL_ORDER: list[str] = [
    "PFS", "AVS", "MDS", "TVS", "EDS", "SMS", "DIA",  # v0.5.0
    "NBV", "BAT", "ECM", "TSA",                        # v0.7.0
    "CCC", "COD",                                       # v0.8.0
    "CIR", "CXS", "FOE", "DCA",                        # v0.10.0
    "BEM", "TPD", "GCD",                                # v0.10.0 (report-only)
    "MAZ", "HSC", "ISD",                                # v1.1.11 (security)
]


def _git_ls_tree(ref: str, path: str) -> list[str]:
    """List filenames under *path* at the given git *ref*."""
    result = subprocess.run(
        ["git", "ls-tree", "--name-only", ref, path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _signals_at_version(tag: str) -> list[str]:
    """Return sorted list of signal abbreviations present at *tag*."""
    entries = _git_ls_tree(tag, "src/drift/signals/")
    abbrevs: list[str] = []
    for entry in entries:
        stem = Path(entry).stem
        if stem.startswith("_") or stem in ("__init__", "base"):
            continue
        abbrev = STEM_TO_ABBREV.get(stem)
        if abbrev:
            abbrevs.append(abbrev)
    return sorted(abbrevs)


def build_matrix(milestones: list[str] | None = None) -> dict:
    """Build the signal coverage matrix across milestones."""
    tags = milestones or MILESTONES
    matrix: dict[str, dict[str, bool]] = {}
    version_totals: dict[str, int] = {}

    all_signals: set[str] = set()
    for tag in tags:
        present = _signals_at_version(tag)
        all_signals.update(present)
        version_totals[tag] = len(present)
        for sig in present:
            matrix.setdefault(sig, {})[tag] = True

    # Fill False for missing signals.
    for sig in all_signals:
        for tag in tags:
            matrix[sig].setdefault(tag, False)

    # Determine introduction version per signal.
    introduced: dict[str, str] = {}
    for sig in all_signals:
        for tag in tags:
            if matrix[sig].get(tag, False):
                introduced[sig] = tag
                break

    # Ordered signal list.
    ordered = [s for s in SIGNAL_ORDER if s in all_signals]
    # Append any unknowns at the end.
    for s in sorted(all_signals):
        if s not in ordered:
            ordered.append(s)

    return {
        "milestones": tags,
        "signals": ordered,
        "matrix": {sig: {tag: matrix[sig][tag] for tag in tags} for sig in ordered},
        "introduced_in": introduced,
        "totals": version_totals,
        "current_total": version_totals.get(tags[-1], 0),
    }


def render_markdown_table(data: dict) -> str:
    """Render the matrix as a Markdown table for STUDY.md."""
    tags = data["milestones"]
    signals = data["signals"]
    matrix = data["matrix"]

    # Header.
    header = "| Signal | " + " | ".join(tags) + " | Introduced |"
    sep = "|--------|" + "|".join(":-:" for _ in tags) + "|------------|"
    rows = [header, sep]

    for sig in signals:
        cells = []
        for tag in tags:
            cells.append("✓" if matrix[sig].get(tag, False) else "—")
        intro = data["introduced_in"].get(sig, "?")
        rows.append(f"| **{sig}** | " + " | ".join(cells) + f" | {intro} |")

    # Totals row.
    totals = data["totals"]
    total_cells = [str(totals.get(t, 0)) for t in tags]
    rows.append("| **Total** | " + " | ".join(total_cells) + " | — |")

    return "\n".join(rows)


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(description="Signal Coverage Matrix generator")
    parser.add_argument(
        "--output",
        default="benchmark_results/signal_coverage_matrix.json",
        help="Output JSON path (default: benchmark_results/signal_coverage_matrix.json)",
    )
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Also print Markdown table to stdout",
    )
    args = parser.parse_args()

    data = build_matrix()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}  ({data['current_total']} signals at latest milestone)")

    if args.markdown:
        print()
        print(render_markdown_table(data))


if __name__ == "__main__":
    main()
