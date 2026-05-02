"""Tests for drift.evidence.schema.json — must match EvidencePackage.model_json_schema().

Analogous to tests/test_config_schema.py.
"""

from __future__ import annotations

import json
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "drift.evidence.schema.json"


def test_schema_file_exists() -> None:
    assert SCHEMA_PATH.exists(), f"Missing: {SCHEMA_PATH}"


def test_schema_matches_model() -> None:
    """Committed schema must match EvidencePackage.model_json_schema() byte-for-byte."""
    from drift_verify._models import EvidencePackage

    expected = EvidencePackage.model_json_schema(by_alias=True)
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected.setdefault("title", "EvidencePackage")
    expected.setdefault("description", "drift-verify Evidence Package v1 schema")

    actual = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert actual == expected, (
        "drift.evidence.schema.json is out of sync. "
        "Run: python scripts/generate_evidence_schema.py"
    )
