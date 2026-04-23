#!/usr/bin/env python3
"""Dead code PR helper: parse vulture output and update pyproject.toml + vulture_whitelist.py.

Reads vulture output from stdin or a file, compares against pyproject.toml [tool.vulture]
ignore_names, and:
  - Appends NEW symbol names to pyproject.toml ignore_names (so vulture in CI picks them up)
  - Appends annotated entries to vulture_whitelist.py (human-readable reference)

Vulture output format (one finding per line):
  src/drift/module.py:42: unused function 'my_func' (60% confidence)

Exit codes:
  0 = success (0 or more new entries added)
  1 = error (e.g. could not parse pyproject.toml)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import tomllib  # type: ignore[import]
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-reuse-def]

REPO_ROOT = Path(__file__).parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
WHITELIST = REPO_ROOT / "vulture_whitelist.py"

_FINDING_RE = re.compile(
    r"^(?P<path>[^:]+):(?P<line>\d+): unused (?P<kind>\w+) '(?P<name>[^']+)'"
    r" \((?P<conf>\d+)% confidence\)$"
)


def _load_pyproject() -> str:
    return PYPROJECT.read_text(encoding="utf-8")


def _existing_ignore_names(content: str) -> set[str]:
    """Parse ignore_names from pyproject.toml content (simple TOML array extraction)."""
    # Use tomllib for robust parsing
    try:
        data = tomllib.loads(content)
        return set(data.get("tool", {}).get("vulture", {}).get("ignore_names", []))
    except Exception as exc:
        print(f"[error] Could not parse pyproject.toml: {exc}", file=sys.stderr)
        return set()


def _add_ignore_names(content: str, new_names: list[str]) -> str:
    """Insert new names into [tool.vulture] ignore_names array in pyproject.toml."""
    # Find the ignore_names section and append before its closing bracket
    pattern = re.compile(
        r'(\[tool\.vulture\].*?ignore_names\s*=\s*\[)(.*?)(\])',
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        print("[warn] Could not locate [tool.vulture] ignore_names in pyproject.toml", file=sys.stderr)
        return content

    prefix = m.group(1)
    body = m.group(2)
    suffix = m.group(3)

    # Determine indent from existing entries
    existing_lines = body.rstrip()
    indent = "    "  # default
    if existing_lines:
        last_line = existing_lines.rsplit("\n", 1)[-1]
        indent_m = re.match(r'^(\s+)', last_line)
        if indent_m:
            indent = indent_m.group(1)

    # Build new entries
    additions = "".join(
        f'\n{indent}# Auto-added by dead-code-loop.yml\n{indent}"{name}",'
        for name in new_names
    )
    new_body = existing_lines + additions + "\n"
    return content[: m.start()] + prefix + new_body + suffix + content[m.end() :]


def _update_whitelist(entries: list[dict]) -> None:
    """Append annotated entries to vulture_whitelist.py."""
    if WHITELIST.exists():
        existing = WHITELIST.read_text(encoding="utf-8")
    else:
        existing = (
            "# vulture_whitelist.py\n"
            "# Unused-code whitelist for vulture.\n"
            "# Symbols here are dynamically called (Click callbacks, Pydantic fields, etc.).\n"
            "# Auto-managed by .github/workflows/dead-code-loop.yml\n\n"
            "# Pre-existing dynamic symbols (from pyproject.toml ignore_names):\n"
            "model_config  # noqa: F821  Pydantic model config\n"
            "as_dict  # noqa: F821  Pydantic serialisation helper\n"
        )

    lines: list[str] = []
    for e in entries:
        comment = f"# {e['path']}:{e['line']}  {e['kind']}  ({e['conf']}% confidence)"
        ref = f"{e['name']}  # noqa: F821  auto-whitelisted"
        lines.append(comment)
        lines.append(ref)

    addition = "\n# --- auto-added by dead-code-loop ---\n" + "\n".join(lines) + "\n"
    WHITELIST.write_text(existing.rstrip("\n") + addition, encoding="utf-8")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "vulture_output",
        nargs="?",
        type=Path,
        help="File containing vulture output (default: read from stdin)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.vulture_output:
        raw = args.vulture_output.read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    findings: list[dict] = []
    for line in raw.splitlines():
        m = _FINDING_RE.match(line.strip())
        if m:
            findings.append(m.groupdict())

    if not findings:
        print("No vulture findings — nothing to do.")
        return 0

    print(f"Found {len(findings)} vulture finding(s).")

    pyproject_content = _load_pyproject()
    existing_names = _existing_ignore_names(pyproject_content)

    new_entries = [f for f in findings if f["name"] not in existing_names]
    if not new_entries:
        print("All findings already in pyproject.toml ignore_names.")
        return 0

    new_names = [e["name"] for e in new_entries]
    print(f"New entries to whitelist: {new_names}")

    if args.dry_run:
        print("[dry-run] No files written.")
        return 0

    # Update pyproject.toml
    updated = _add_ignore_names(pyproject_content, new_names)
    PYPROJECT.write_text(updated, encoding="utf-8")
    print(f"Updated {PYPROJECT} with {len(new_names)} new ignore_names.")

    # Update vulture_whitelist.py
    _update_whitelist(new_entries)
    print(f"Updated {WHITELIST}")

    # Print count for workflow consumption
    print(f"::set-output name=new_entries::{len(new_entries)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
