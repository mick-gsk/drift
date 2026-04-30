#!/usr/bin/env python3
"""Insert a CHANGELOG entry into CHANGELOG.md in-place.

Two input modes:
  --commit-type feat|fix|chore  --message "text"   (explicit args)
  --from-commit-msg FILE                            (git hook mode)

Add --dry-run to preview the result without writing.

Insertion rules:
  1. If ## [VERSION] already exists: merge bullet into the correct
     ### Added / Fixed / Changed subsection within that block.
     If the subsection is absent it is created at the end of the block.
  2. If ## [VERSION] does not yet exist: prepend a new ## [VERSION] block
     before the first existing ## [x.y.z] entry.

The script is idempotent: if the exact bullet is already present it exits 0
without modifying the file.

Exit codes:
  0  success (or graceful skip for non-conventional commits)
  1  error (bad arguments, I/O failure, etc.)
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"

SECTION_MAP: dict[str, str] = {
    "feat": "Added",
    "fix": "Fixed",
    "chore": "Changed",
}

# Matches "feat(scope): message", "fix!: message", etc.
CONVENTIONAL_RE = re.compile(
    r"^(feat|fix|chore)(?:\([^)]*\))?!?: (.+)",
    re.IGNORECASE,
)

VERSION_HEADER_RE = re.compile(r"^## \[(\d+\.\d+[\.\d]*)\]")
SECTION_HEADER_RE = re.compile(r"^### (Added|Fixed|Changed|Removed|Deprecated|Security)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_version() -> str:
    with (REPO_ROOT / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return str(data["project"]["version"])


def _parse_commit_msg(path: str) -> tuple[str, str] | None:
    """Return (commit_type, message) or None for non-conventional commits."""
    try:
        text = Path(path).read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return None
    m = CONVENTIONAL_RE.match(text)
    if not m:
        return None
    return m.group(1).lower(), m.group(2).strip()


def _find_block(lines: list[str], version: str) -> tuple[int, int] | None:
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


# ---------------------------------------------------------------------------
# Core integration
# ---------------------------------------------------------------------------


def integrate(
    *,
    commit_type: str,
    message: str,
    version: str,
    changelog: Path = CHANGELOG,
    dry_run: bool = False,
) -> bool:
    """Insert entry; return True if file was (or would be) modified."""
    section_name = SECTION_MAP[commit_type]
    bullet = f"- {message}"
    date_str = dt.date.today().isoformat()

    lines = changelog.read_text(encoding="utf-8").splitlines(keepends=True)

    block = _find_block(lines, version)

    if block is not None:
        block_start, block_end = block
        section_line, next_section = _find_section_in_block(
            lines, block_start, block_end, section_name
        )

        if section_line is None:
            # Section absent — create it at the end of the block (before blank lines).
            insert_at = block_end
            for i in range(block_end - 1, block_start, -1):
                if lines[i].strip():
                    insert_at = i + 1
                    break
            new_lines: list[str] = [f"\n### {section_name}\n", f"{bullet}\n"]
            lines[insert_at:insert_at] = new_lines
        else:
            # Section present — find insertion point after last bullet.
            limit = next_section if next_section is not None else block_end
            insert_at = section_line + 1
            while insert_at < limit:
                stripped = lines[insert_at].rstrip("\n")
                if stripped.startswith("- "):
                    if stripped == bullet:
                        return False  # already present — idempotent skip
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
        new_block: list[str] = [
            f"## [{version}] - {date_str}\n",
            "\n",
            f"Short version: {message}\n",
            "\n",
            f"### {section_name}\n",
            f"{bullet}\n",
            "\n",
        ]
        lines[insert_at:insert_at] = new_block

    result = "".join(lines)
    if dry_run:
        sys.stdout.buffer.write(result.encode("utf-8"))
        return True
    changelog.write_text(result, encoding="utf-8")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Insert a CHANGELOG entry into CHANGELOG.md in-place."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--commit-type",
        choices=list(SECTION_MAP),
        help="Conventional commit type (explicit mode).",
    )
    group.add_argument(
        "--from-commit-msg",
        metavar="FILE",
        help="Path to git COMMIT_EDITMSG (hook mode).",
    )
    parser.add_argument(
        "--message",
        help="Changelog bullet text (required with --commit-type).",
    )
    parser.add_argument(
        "--version",
        default="",
        help="Version override; defaults to pyproject.toml version.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resulting CHANGELOG.md to stdout without writing.",
    )
    args = parser.parse_args()

    if args.from_commit_msg:
        parsed = _parse_commit_msg(args.from_commit_msg)
        if parsed is None:
            # Non-conventional commit or unrecognised type — skip gracefully.
            return 0
        commit_type, message = parsed
    else:
        if not args.message:
            parser.error("--message is required when using --commit-type.")
        commit_type = args.commit_type
        message = args.message

    version = args.version or _read_version()

    try:
        changed = integrate(
            commit_type=commit_type,
            message=message,
            version=version,
            dry_run=args.dry_run,
        )
    except OSError as exc:
        print(f">>> [changelog] ERROR: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        return 0
    if changed:
        print(
            f">>> [changelog] Inserted [{version}] ### {SECTION_MAP[commit_type]}: {message}"
        )
    else:
        print(">>> [changelog] Entry already present — skipped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
