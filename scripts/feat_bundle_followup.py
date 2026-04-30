#!/usr/bin/env python3
"""Automated follow-up after `make feat-bundle`.

Inserts a CHANGELOG entry and prepends a STUDY.md stub using metadata
from a generated feature-evidence JSON artifact.

Usage::

    python scripts/feat_bundle_followup.py \\
        benchmark_results/vX.Y.Z_slug_feature_evidence.json

    python scripts/feat_bundle_followup.py \\
        benchmark_results/vX.Y.Z_slug_feature_evidence.json \\
        --msg "Human-readable description of the feature"

    python scripts/feat_bundle_followup.py \\
        benchmark_results/vX.Y.Z_slug_feature_evidence.json \\
        --dry-run

If ``--msg`` is omitted, a ``TODO:`` placeholder is inserted so the
generated entries remain visibly incomplete and trigger a pre-push
Study.md freshness gate warning.

Exit codes:
    0  success
    1  error (missing file, JSON parse failure, I/O error)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
STUDY_MD = REPO_ROOT / "docs" / "STUDY.md"

VERSION_HEADER_RE = re.compile(r"^## \[(\d+\.\d+[\.\d]*)\]")
SECTION_HEADER_RE = re.compile(r"^### (Added|Fixed|Changed|Removed|Deprecated|Security)")


# ---------------------------------------------------------------------------
# Evidence JSON helpers
# ---------------------------------------------------------------------------


def _load_evidence(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Error: evidence file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(1)


def _title_from_feature(feature: str) -> str:
    """Convert slug/feature string to title-case heading."""
    return " ".join(w.capitalize() for w in feature.split())


# ---------------------------------------------------------------------------
# CHANGELOG helpers (adapted from integrate_changelog_entry.py)
# ---------------------------------------------------------------------------


def _find_version_block(lines: list[str], version: str) -> tuple[int, int] | None:
    """Return (start, end) line indices for the ## [version] block, or None."""
    start: int | None = None
    for i, line in enumerate(lines):
        m = VERSION_HEADER_RE.match(line)
        if m:
            if m.group(1) == version:
                start = i
            elif start is not None:
                return start, i
    if start is not None:
        return start, len(lines)
    return None


def _find_section_in_block(
    lines: list[str],
    block_start: int,
    block_end: int,
    section_name: str,
) -> tuple[int | None, int | None]:
    """Return (section_line, next_section_line) within the block."""
    section_line: int | None = None
    for i in range(block_start + 1, block_end):
        m = SECTION_HEADER_RE.match(lines[i].rstrip("\n"))
        if m:
            if m.group(1) == section_name:
                section_line = i
            elif section_line is not None:
                return section_line, i
    return section_line, None


def _integrate_changelog(
    *,
    version: str,
    title: str,
    bullet: str,
    date_str: str,
    changelog: Path,
    dry_run: bool,
) -> bool:
    """Insert CHANGELOG entry; return True if file was (or would be) modified."""
    section_name = "Added"
    lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)

    block = _find_version_block(lines, version)

    if block is not None:
        block_start, block_end = block
        section_line, next_section = _find_section_in_block(
            lines, block_start, block_end, section_name
        )
        if section_line is None:
            # Section absent — append at end of block.
            insert_at = block_end
            for i in range(block_end - 1, block_start, -1):
                if lines[i].strip():
                    insert_at = i + 1
                    break
            lines[insert_at:insert_at] = [f"\n### {section_name}\n", f"{bullet}\n"]
        else:
            limit = next_section if next_section is not None else block_end
            insert_at = section_line + 1
            while insert_at < limit:
                stripped = lines[insert_at].rstrip("\n")
                if stripped.startswith("- "):
                    if stripped == bullet:
                        return False  # idempotent skip
                    insert_at += 1
                else:
                    break
            lines.insert(insert_at, f"{bullet}\n")
    else:
        # No existing version block — prepend before the first ## [x.y.z] line.
        insert_at = len(lines)
        for i, line in enumerate(lines):
            if VERSION_HEADER_RE.match(line):
                insert_at = i
                break
        short_version = title if title else bullet.lstrip("- ")
        lines[insert_at:insert_at] = [
            f"## [{version}] - {date_str}\n",
            "\n",
            f"Short version: {short_version}\n",
            "\n",
            f"### {section_name}\n",
            f"{bullet}\n",
            "\n",
        ]

    result = "".join(lines)
    if dry_run:
        print("=== CHANGELOG.md (dry-run) ===")
        # Print only first 40 lines for readability.
        preview_lines = result.splitlines()[:40]
        print("\n".join(preview_lines))
        print("...")
        return True
    changelog.write_text(result, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# STUDY.md helper
# ---------------------------------------------------------------------------


def _prepend_study_entry(
    *,
    version: str,
    date_str: str,
    title: str,
    msg: str,
    evidence_filename: str,
    study: Path,
    dry_run: bool,
) -> bool:
    """Prepend a feature update stub to STUDY.md after the H1 header."""
    content = study.read_text(encoding="utf-8")

    stub = (
        f"\n> **Feature update ({date_str}, v{version}: {title}):** "
        f"{msg} "
        f"Evidence: `benchmark_results/{evidence_filename}`.\n"
    )

    # Check for idempotency: already has this version/title combo.
    if f"v{version}: {title}" in content:
        return False

    # Insert stub right after the first H1 heading line.
    # Strip BOM before processing so startswith("# ") works reliably.
    lines = content.lstrip("\ufeff").splitlines(keepends=True)
    insert_at = 1  # default: after line 0
    for i, line in enumerate(lines):
        if line.lstrip("\ufeff").startswith("# "):
            insert_at = i + 1
            break

    lines.insert(insert_at, stub)
    result = "".join(lines)

    if dry_run:
        print("\n=== docs/STUDY.md (dry-run, first 20 lines) ===")
        print("\n".join(result.splitlines()[:20]))
        print("...")
        return True
    study.write_text(result, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Automated CHANGELOG + STUDY.md follow-up after make feat-bundle."
    )
    parser.add_argument(
        "evidence",
        type=Path,
        help=(
            "Path to the feature-evidence JSON "
            "(e.g. benchmark_results/vX.Y.Z_slug_feature_evidence.json)."
        ),
    )
    parser.add_argument(
        "--msg",
        default="",
        help=(
            "Human-readable description inserted into CHANGELOG and STUDY.md. "
            "Defaults to a TODO placeholder."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--changelog-only",
        action="store_true",
        help="Only update CHANGELOG.md.",
    )
    parser.add_argument(
        "--study-only",
        action="store_true",
        help="Only update docs/STUDY.md.",
    )
    args = parser.parse_args()

    if args.changelog_only and args.study_only:
        print("Error: --changelog-only and --study-only are mutually exclusive.", file=sys.stderr)
        return 1

    evidence_path = args.evidence
    if not evidence_path.is_absolute():
        evidence_path = Path.cwd() / evidence_path

    ev = _load_evidence(evidence_path)

    version: str = ev.get("version", "")
    if not version:
        print("Error: evidence JSON missing 'version' field.", file=sys.stderr)
        return 1

    feature: str = ev.get("feature", "")
    title = _title_from_feature(feature) if feature else f"v{version} feature"
    date_str: str = ev.get("date", dt.date.today().isoformat())
    evidence_filename = evidence_path.name

    # Determine bullet message.
    msg = args.msg.strip()
    if not msg:
        msg = f"TODO: describe {title} feature (auto-stub from feat-bundle)."

    bullet = f"- {msg}"

    changed: list[str] = []

    if not args.study_only:
        if _integrate_changelog(
            version=version,
            title=title,
            bullet=bullet,
            date_str=date_str,
            changelog=CHANGELOG,
            dry_run=args.dry_run,
        ):
            changed.append("CHANGELOG.md")
        else:
            print(f"CHANGELOG.md: v{version} entry already up-to-date — skipped.")

    if not args.changelog_only:
        if _prepend_study_entry(
            version=version,
            date_str=date_str,
            title=title,
            msg=msg,
            evidence_filename=evidence_filename,
            study=STUDY_MD,
            dry_run=args.dry_run,
        ):
            changed.append("docs/STUDY.md")
        else:
            print(f"docs/STUDY.md: v{version} entry already present — skipped.")

    if changed and not args.dry_run:
        print(f"Updated: {', '.join(changed)}")
        if "TODO:" in msg:
            print(
                "Reminder: replace the TODO placeholder in the updated files "
                "with a real description before pushing."
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
