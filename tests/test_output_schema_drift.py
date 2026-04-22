"""CI gate for drift.output.schema.json (Paket 1B, ADR-090).

Ensures the checked-in JSON schema stays in sync with the code-defined
generator and that a real ``analysis_to_json`` output — including the
``agent_telemetry`` block — validates against it.
"""

from __future__ import annotations

import datetime
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft7Validator

from drift.models import (
    OUTPUT_SCHEMA_VERSION,
    AgentAction,
    AgentActionType,
    AgentTelemetry,
    Finding,
    ModuleScore,
    RepoAnalysis,
    Severity,
    SignalType,
)
from drift.output.json_output import analysis_to_json

pytestmark = pytest.mark.contract

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "drift.output.schema.json"
GENERATOR = REPO_ROOT / "scripts" / "generate_output_schema.py"


def _make_analysis(agent_telemetry: AgentTelemetry | None = None) -> RepoAnalysis:
    finding = Finding(
        signal_type=SignalType.PATTERN_FRAGMENTATION,
        severity=Severity.LOW,
        score=0.15,
        title="Minor fragmentation",
        description="Test finding.",
        file_path=Path("src/app/service.py"),
        start_line=5,
        impact=0.1,
    )
    module = ModuleScore(
        path=Path("src/app"),
        drift_score=0.2,
        signal_scores={SignalType.PATTERN_FRAGMENTATION: 0.2},
        findings=[finding],
        ai_ratio=0.0,
    )
    return RepoAnalysis(
        repo_path=Path("."),
        analyzed_at=datetime.datetime(2026, 4, 22, tzinfo=datetime.UTC),
        drift_score=0.2,
        module_scores=[module],
        findings=[finding],
        total_files=5,
        total_functions=15,
        ai_attributed_ratio=0.0,
        analysis_duration_seconds=0.5,
        agent_telemetry=agent_telemetry,
    )


class TestSchemaGeneratorDrift:
    """`drift.output.schema.json` must stay in sync with the generator."""

    def test_schema_file_is_up_to_date(self) -> None:
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "--check"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"drift.output.schema.json is out of date.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}\n"
            f"Fix: `python scripts/generate_output_schema.py "
            f"-o drift.output.schema.json`"
        )

    def test_schema_version_matches_code(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        assert schema["properties"]["schema_version"]["const"] == OUTPUT_SCHEMA_VERSION


class TestAgentTelemetrySchemaShape:
    """Schema must describe the agent_telemetry block (ADR-090)."""

    @pytest.fixture
    def schema(self) -> dict[str, Any]:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_agent_telemetry_property_present(self, schema: dict[str, Any]) -> None:
        assert "agent_telemetry" in schema["properties"]

    def test_agent_telemetry_allows_null(self, schema: dict[str, Any]) -> None:
        node = schema["properties"]["agent_telemetry"]
        assert "null" in node["type"]

    def test_agent_action_type_enum_complete(self, schema: dict[str, Any]) -> None:
        """Schema enum must match the AgentActionType StrEnum values exactly."""
        node = schema["properties"]["agent_telemetry"]
        action_schema = node["properties"]["agent_actions_taken"]["items"]
        schema_enum = set(action_schema["properties"]["action_type"]["enum"])
        code_enum = {member.value for member in AgentActionType}
        assert schema_enum == code_enum, (
            f"AgentActionType enum drift: schema={schema_enum!r} code={code_enum!r}"
        )

    def test_gate_enum_matches_severity_gate(self, schema: dict[str, Any]) -> None:
        node = schema["properties"]["agent_telemetry"]
        action_schema = node["properties"]["agent_actions_taken"]["items"]
        gate_values = set(action_schema["properties"]["gate"]["enum"])
        # Must be exactly {AUTO, REVIEW, BLOCK, null} per ADR-089.
        assert gate_values == {"AUTO", "REVIEW", "BLOCK", None}


class TestGeneratedJsonValidatesAgainstSchema:
    """Real analysis_to_json output validates against the checked-in schema."""

    @pytest.fixture
    def validator(self) -> Draft7Validator:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        return Draft7Validator(schema)

    def test_analysis_without_telemetry_validates(self, validator: Draft7Validator) -> None:
        data = json.loads(analysis_to_json(_make_analysis()))
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        assert errors == [], "\n".join(str(e) for e in errors)

    def test_analysis_with_agent_telemetry_validates(self, validator: Draft7Validator) -> None:
        telemetry = AgentTelemetry(
            session_id="ses-1",
            agent_actions_taken=[
                AgentAction(
                    action_type=AgentActionType.AUTO_FIX,
                    reason="low severity auto-repair",
                    finding_id="abcdef0123456789",
                    severity="low",
                    gate="AUTO",
                    safe_to_commit=True,
                    timestamp="2026-04-22T12:00:00Z",
                ),
                AgentAction(
                    action_type=AgentActionType.BLOCK,
                    reason="critical finding blocks CI",
                    finding_id="fedcba9876543210",
                    severity="critical",
                    gate="BLOCK",
                ),
            ],
        )
        data = json.loads(analysis_to_json(_make_analysis(telemetry)))
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        assert errors == [], "\n".join(str(e) for e in errors)

    def test_invalid_gate_value_rejected(self, validator: Draft7Validator) -> None:
        """Schema must reject gate values outside {AUTO, REVIEW, BLOCK, null}."""
        data = json.loads(analysis_to_json(_make_analysis()))
        data["agent_telemetry"] = {
            "schema_version": "2.2",
            "session_id": None,
            "total_auto": 0,
            "total_review": 0,
            "total_block": 0,
            "agent_actions_taken": [
                {
                    "action_type": "auto_fix",
                    "reason": "x",
                    "gate": "MAYBE",  # invalid per ADR-089
                }
            ],
        }
        errors = list(validator.iter_errors(data))
        assert any("gate" in list(e.path) for e in errors), (
            f"schema accepted invalid gate value; errors={errors!r}"
        )
