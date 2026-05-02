#!/usr/bin/env python3
"""
Build Instruction Discovery Registry.

Generates work_artifacts/instruction_discovery.json with a machine-readable
overview of all .instructions.md files in .github/instructions/.

Exit code: 0 always (generator, not validator).
"""

import json
import sys
from pathlib import Path

import yaml


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
        frontmatter = yaml.safe_load(frontmatter_str) or {}
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
