#!/usr/bin/env python
"""Generate JSON Schema for EvidencePackage and write to drift.evidence.schema.json.

Analogous to scripts/generate_output_schema.py.

Usage:
    python scripts/generate_evidence_schema.py [--output PATH]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def build_schema() -> dict:
    """Return JSON Schema dict for EvidencePackage (evidence-package-v1)."""
    from drift_verify._models import EvidencePackage

    schema = EvidencePackage.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema.setdefault("title", "EvidencePackage")
    schema.setdefault("description", "drift-verify Evidence Package v1 schema")
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("drift.evidence.schema.json"),
        help="Output path (default: drift.evidence.schema.json)",
    )
    args = parser.parse_args()

    schema = build_schema()
    args.output.write_text(
        json.dumps(schema, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Written: {args.output}")


if __name__ == "__main__":
    main()
