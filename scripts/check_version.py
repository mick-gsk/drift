#!/usr/bin/env python3
"""
Version consistency guard for the drift release process.

Enforces:
  - pyproject.toml version is always valid SemVer (MAJOR.MINOR.PATCH)
  - A full version tag (v1.2.3) matches the version in pyproject.toml
  - Major-only tags (v1, v2) are rejected for human pushes
    (they are managed exclusively by the release automation)

Usage:
  python scripts/check_version.py --tag v1.1.1     # validate tag vs pyproject.toml
  python scripts/check_version.py --check-semver   # only validate pyproject.toml format

Exit codes:
  0 – all checks passed
  1 – at least one check failed (details printed to stdout)
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path

# ------------------------------------------------------------------
# Patterns
# ------------------------------------------------------------------
_SEMVER_FULL = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_SEMVER_MAJOR = re.compile(r"^v(\d+)$")


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _fail(msg: str) -> None:
    print(f"ERROR: {msg}", flush=True)
    sys.exit(1)


def _get_pyproject_version() -> str:
    """Return the project.version string from pyproject.toml."""
    path = Path(__file__).parent.parent / "pyproject.toml"
    if not path.exists():
        _fail(f"pyproject.toml not found at {path}")
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    try:
        return data["project"]["version"]
    except KeyError:
        _fail("pyproject.toml does not contain [project] version field")
    raise AssertionError("unreachable")  # satisfy type checker – _fail calls sys.exit


def _ok(msg: str) -> None:
    print(f"OK: {msg}", flush=True)


# ------------------------------------------------------------------
# Checks
# ------------------------------------------------------------------
def check_pyproject_semver(version: str) -> None:
    """Fail if *version* is not in MAJOR.MINOR.PATCH format."""
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        _fail(
            f"pyproject.toml version '{version}' is not valid SemVer.\n"
            "       Expected format: MAJOR.MINOR.PATCH (e.g. 1.2.3)"
        )
    _ok(f"pyproject.toml version '{version}' is valid SemVer")


def check_tag_against_pyproject(tag: str, pyproject_version: str) -> None:
    """
    Validate that *tag* is a full SemVer tag AND matches *pyproject_version*.

    Rejects:
      - Tags that are major-only (v1, v2) – those belong to automation only.
      - Tags that don't follow vMAJOR.MINOR.PATCH.
      - Tags whose version doesn't match pyproject.toml.
    """
    # Block major-only tags (e.g. "v1") – managed exclusively by automation
    if _SEMVER_MAJOR.match(tag) and not _SEMVER_FULL.match(tag):
        _fail(
            f"Tag '{tag}' is a major-only tag (e.g. v1).\n"
            "       Major tags are moved automatically by the release workflow.\n"
            "       Create a full SemVer tag instead: v{MAJOR}.{MINOR}.{PATCH}"
        )

    m = _SEMVER_FULL.match(tag)
    if not m:
        _fail(
            f"Tag '{tag}' does not match the required format vMAJOR.MINOR.PATCH.\n"
            "       Examples of valid tags: v1.1.0, v1.2.0, v2.0.0"
        )
        raise AssertionError("unreachable")

    tag_version = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
    if tag_version != pyproject_version:
        _fail(
            f"Version mismatch:\n"
            f"         git tag    → {tag}  (implies {tag_version})\n"
            f"         pyproject  → {pyproject_version}\n"
            "       Update pyproject.toml to match the tag before releasing:\n"
            f'         version = "{tag_version}"'
        )

    _ok(f"Tag '{tag}' matches pyproject.toml version '{pyproject_version}'")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Validate version consistency for drift releases.")
    parser.add_argument(
        "--tag",
        metavar="TAG",
        help="Git tag to validate against pyproject.toml (e.g. v1.2.3)",
    )
    parser.add_argument(
        "--check-semver",
        action="store_true",
        help="Only validate that pyproject.toml version is valid SemVer",
    )
    args = parser.parse_args()

    if not args.tag and not args.check_semver:
        parser.error("Provide --tag <TAG> or --check-semver")

    version = _get_pyproject_version()
    check_pyproject_semver(version)

    if args.tag:
        check_tag_against_pyproject(args.tag, version)


if __name__ == "__main__":
    main()
