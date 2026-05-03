#!/usr/bin/env python3
"""
Build Instruction Discovery Registry.

Generates work_artifacts/instruction_discovery.json with a machine-readable
overview of all .instructions.md files in .github/instructions/.

Exit code: 0 always (generator, not validator).
"""

import json
import re
import sys
from pathlib import Path


def _parse_simple_frontmatter(frontmatter_str: str) -> dict:
    """Parse simple YAML frontmatter using stdlib only.

    Handles the two patterns used in .instructions.md files:
      - Scalar: key: "value" or key: value
      - Sequence: key:\\n  - item1\\n  - item2
    """
    result: dict = {}
    lines = frontmatter_str.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Skip blank lines and comments
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        # Match a top-level key (no leading whitespace)
        key_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)', line)
        if not key_match:
            i += 1
            continue
        key = key_match.group(1)
        raw_value = key_match.group(2).strip()
        if raw_value == "":
            # Possibly a block sequence follows
            items = []
            j = i + 1
            while j < len(lines) and re.match(r'^\s+-\s+', lines[j]):
                item = re.sub(r'^\s+-\s+', '', lines[j]).strip().strip('"\'')
                items.append(item)
                j += 1
            if items:
                result[key] = items
                i = j
            else:
                result[key] = None
                i += 1
        else:
            # Strip surrounding quotes if present
            result[key] = raw_value.strip('"\'')
            i += 1
    return result


def extract_frontmatter(file_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file.

    Returns dict with 'applyTo' and 'description' keys (both may be None).
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return {"applyTo": None, "description": None}

    if not content.startswith("---"):
        return {"applyTo": None, "description": None}

    try:
        # Find end of frontmatter
        end_marker = content.find("\n---\n", 4)
        if end_marker == -1:
            return {"applyTo": None, "description": None}

        frontmatter_str = content[4:end_marker]
        frontmatter = _parse_simple_frontmatter(frontmatter_str)
    except Exception as e:
        print(f"Warning: Could not parse frontmatter in {file_path}: {e}", file=sys.stderr)
        return {"applyTo": None, "description": None}

    apply_to = frontmatter.get("applyTo")
    description = frontmatter.get("description")

    return {"applyTo": apply_to, "description": description}


def build_registry() -> list:
    """Scan .github/instructions/ and build registry."""
    instructions_dir = Path(".github/instructions")
    if not instructions_dir.exists():
        print(f"Warning: {instructions_dir} does not exist", file=sys.stderr)
        return []

    registry = []
    for file_path in sorted(instructions_dir.glob("*.instructions.md")):
        frontmatter = extract_frontmatter(file_path)
        registry.append(
            {
                "file": file_path.as_posix(),
                "applyTo": frontmatter["applyTo"],
                "description": frontmatter["description"],
                "has_description": frontmatter["description"] is not None,
                "has_applyTo": frontmatter["applyTo"] is not None,
            }
        )

    return registry


def main():
    """Generate and write registry."""
    registry = build_registry()

    # Ensure work_artifacts directory exists
    work_artifacts = Path("work_artifacts")
    work_artifacts.mkdir(exist_ok=True)

    output_file = work_artifacts / "instruction_discovery.json"

    # Write with deterministic formatting (sort_keys, no trailing newline issues)
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=False, ensure_ascii=False)
        f.write("\n")

    print(f"Generated {output_file} with {len(registry)} instructions", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
