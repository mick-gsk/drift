from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_agent_harness_contract.py"


def load_agent_harness_contract_module() -> Any:
    spec = importlib.util.spec_from_file_location("check_agent_harness_contract", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["check_agent_harness_contract"] = module
    spec.loader.exec_module(module)
    return module


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_required_paths_reports_missing_files_with_remediation(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()

    violations = module.check_required_paths(
        tmp_path,
        required_paths=["AGENTS.md", "audit/harness-engine-audit.md"],
    )

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS001", "AGENTS.md"),
        ("HARNESS001", "audit/harness-engine-audit.md"),
    ]
    assert all("Create" in item.remediation for item in violations)


def test_root_allowlist_must_include_new_harness_entries(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(tmp_path / ".github" / "repo-root-allowlist", "README.md\n")

    violations = module.check_root_allowlist_entries(
        tmp_path,
        required_entries=["AGENTS.md", "audit"],
    )

    assert len(violations) == 1
    assert violations[0].code == "HARNESS002"
    assert violations[0].path == ".github/repo-root-allowlist"
    assert "AGENTS.md" in violations[0].message
    assert "audit" in violations[0].message


def test_markdown_link_check_flags_missing_local_targets(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "AGENTS.md",
        "[ok](docs/existing.md) [missing](docs/missing.md) "
        "[external](https://example.com) [anchor](#local)\n",
    )
    write_text(tmp_path / "docs" / "existing.md", "# Existing\n")

    violations = module.check_markdown_local_links(tmp_path, docs=["AGENTS.md"])

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS003", "AGENTS.md"),
    ]
    assert "docs/missing.md" in violations[0].message
    assert "Fix the link target" in violations[0].remediation


def test_mcp_boundary_contract_blocks_router_importing_server(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(tmp_path / "src" / "drift" / "mcp_server.py", "from drift.mcp_utils import x\n")
    write_text(
        tmp_path / "src" / "drift" / "mcp_router_analysis.py",
        "from drift.mcp_server import mcp\n",
    )

    violations = module.check_mcp_boundary_contract(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS004", "src/drift/mcp_router_analysis.py"),
    ]
    assert "must not import drift.mcp_server" in violations[0].message


def test_mcp_boundary_contract_blocks_server_business_logic_imports(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(tmp_path / "src" / "drift" / "mcp_server.py", "from drift.api import scan\n")
    write_text(
        tmp_path / "src" / "drift" / "mcp_router_analysis.py",
        "from drift.api import scan\n",
    )

    violations = module.check_mcp_boundary_contract(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS005", "src/drift/mcp_server.py"),
    ]
    assert "registration shell" in violations[0].message


def test_format_violations_is_agent_readable() -> None:
    module = load_agent_harness_contract_module()
    violation = module.Violation(
        code="HARNESS999",
        path="AGENTS.md",
        message="Example failure.",
        remediation="Repair it.",
    )

    formatted = module.format_violations([violation])

    assert "HARNESS999" in formatted
    assert "AGENTS.md" in formatted
    assert "Remediation: Repair it." in formatted


# ---------------------------------------------------------------------------
# HARNESS006 / HARNESS007 — MCP tool router-ownership invariants
# ---------------------------------------------------------------------------


_FAKE_SERVER_OK = '''\
import json
from drift.mcp_utils import x

@mcp.tool()
async def drift_scan(path: str = ".") -> str:
    """Scan."""
    from drift.mcp_router_analysis import run_scan

    return await run_scan(path=path)


@mcp.tool()
async def drift_legacy(x: str = "") -> str:
    """Legacy."""
    from drift.mcp_legacy import run_x

    return await run_x()
'''


_FAKE_SERVER_NO_OWNER = '''\
@mcp.tool()
async def drift_inline(path: str = ".") -> str:
    """Inline business logic — should be flagged."""
    return "{}"
'''


def _write_fake_server(tmp_path: Path, body: str) -> None:
    write_text(tmp_path / "src" / "drift" / "mcp_server.py", body)


def test_parse_mcp_tools_extracts_name_lineno_and_owner(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    _write_fake_server(tmp_path, _FAKE_SERVER_OK)

    entries = module.parse_mcp_tools_from_server(tmp_path)

    assert [(entry["name"], entry["owner"]) for entry in entries] == [
        ("drift_scan", "drift.mcp_router_analysis"),
        ("drift_legacy", "drift.mcp_legacy"),
    ]
    assert all(isinstance(entry["lineno"], int) and entry["lineno"] > 0 for entry in entries)


def test_check_tool_ownership_flags_drift_between_source_and_map(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    _write_fake_server(tmp_path, _FAKE_SERVER_OK)
    write_text(
        tmp_path / "audit" / "harness-tool-map.json",
        json.dumps(
            {
                "version": 1,
                "tools": [
                    {
                        "name": "drift_scan",
                        "lineno": 4,
                        "owner": "drift.mcp_router_analysis",
                    },
                ],
                "inline_allowed": [],
            }
        )
        + "\n",
    )

    violations = module.check_mcp_tool_router_ownership(tmp_path)

    codes = [item.code for item in violations]
    assert "HARNESS006" in codes
    drift_violation = next(item for item in violations if item.code == "HARNESS006")
    assert "drift_legacy" in drift_violation.message
    assert "--write-tool-map" in drift_violation.remediation


def test_check_tool_ownership_flags_inline_tool_without_allowlist(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    _write_fake_server(tmp_path, _FAKE_SERVER_NO_OWNER)
    # Pre-write the matching map so HARNESS006 does not also fire.
    expected = module.build_tool_map(tmp_path, inline_allowed=[])
    write_text(
        tmp_path / "audit" / "harness-tool-map.json",
        json.dumps(expected, indent=2) + "\n",
    )

    violations = module.check_mcp_tool_router_ownership(tmp_path)

    codes = [item.code for item in violations]
    assert codes == ["HARNESS007"]
    assert "drift_inline" in violations[0].message
    assert "inline_allowed" in violations[0].remediation


def test_check_tool_ownership_respects_inline_allowlist(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    _write_fake_server(tmp_path, _FAKE_SERVER_NO_OWNER)
    expected = module.build_tool_map(tmp_path, inline_allowed=["drift_inline"])
    write_text(
        tmp_path / "audit" / "harness-tool-map.json",
        json.dumps(expected, indent=2) + "\n",
    )

    violations = module.check_mcp_tool_router_ownership(tmp_path)

    assert violations == []


def test_write_tool_map_preserves_inline_allowed(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    _write_fake_server(tmp_path, _FAKE_SERVER_OK)
    map_path = tmp_path / "audit" / "harness-tool-map.json"
    write_text(
        map_path,
        json.dumps({"version": 1, "tools": [], "inline_allowed": ["drift_keep_me"]}) + "\n",
    )

    module.write_tool_map(tmp_path)

    data = json.loads(map_path.read_text(encoding="utf-8"))
    assert data["inline_allowed"] == ["drift_keep_me"]
    assert {entry["name"] for entry in data["tools"]} == {"drift_scan", "drift_legacy"}


def test_ab_harness_make_target_requires_neutral_mock_mode(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "Makefile",
        "ab-harness:\n"
        "\t$(PYTHON) scripts/ab_harness.py run\n"
        "\t$(PYTHON) scripts/ab_harness.py stats\n"
        "\t$(PYTHON) scripts/ab_harness.py report\n",
    )

    checker = getattr(module, "check_ab_harness_target_uses_neutral_mock", None)
    assert checker is not None
    violations = checker(tmp_path)

    assert [(item.code, item.path) for item in violations] == [("HARNESS008", "Makefile")]
    assert "--mock-mode neutral" in violations[0].remediation


def test_ab_harness_make_target_accepts_neutral_mock_mode(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "Makefile",
        "ab-harness:\n"
        "\t$(PYTHON) scripts/ab_harness.py run --mock-mode neutral\n"
        "\t$(PYTHON) scripts/ab_harness.py stats\n"
        "\t$(PYTHON) scripts/ab_harness.py report\n",
    )

    checker = getattr(module, "check_ab_harness_target_uses_neutral_mock", None)
    assert checker is not None

    assert checker(tmp_path) == []


def test_failed_turn_repro_bundle_contract_requires_script(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()

    checker = getattr(module, "check_failed_turn_repro_bundle_contract", None)
    assert checker is not None
    violations = checker(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS009", "scripts/agent_repro_bundle.py")
    ]
    assert "failed agent-turn repro bundle" in violations[0].message


def test_failed_turn_repro_bundle_contract_requires_core_fields(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "scripts" / "agent_repro_bundle.py",
        "REPRO_BUNDLE_REQUIRED_FIELDS = ('schema_version', 'session_summary')\n"
        "def write_bundle():\n"
        "    return 'manifest.json README.md'\n",
    )

    violations = module.check_failed_turn_repro_bundle_contract(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS009", "scripts/agent_repro_bundle.py")
    ]


def test_failed_turn_repro_bundle_contract_requires_makefile_target(tmp_path: Path) -> None:
    """HARNESS009 must fire when Makefile has no repro-bundle target."""
    module = load_agent_harness_contract_module()
    fields = (
        "REPRO_BUNDLE_REQUIRED_FIELDS = ("
        "'schema_version', 'created_at', 'session_summary', 'failure_context', "
        "'changed_files', 'diff_stat', 'last_check_status', 'last_nudge_status', "
        "'next_agent_entrypoint', 'git_branch', 'git_head')\n"
    )
    write_text(
        tmp_path / "scripts" / "agent_repro_bundle.py",
        fields + "def write_bundle(): return 'manifest.json README.md diff.patch'\n",
    )
    # Makefile without repro-bundle target
    write_text(
        tmp_path / "Makefile",
        "agent-harness-check:\n\t$(PYTHON) scripts/check_agent_harness_contract.py --root .\n",
    )

    violations = module.check_failed_turn_repro_bundle_contract(tmp_path)

    assert any(
        item.code == "HARNESS009" and "repro-bundle" in item.message for item in violations
    )


def test_failed_turn_repro_bundle_contract_accepts_makefile_with_target(tmp_path: Path) -> None:
    """HARNESS009 must NOT fire when Makefile declares repro-bundle target."""
    module = load_agent_harness_contract_module()
    fields = (
        "REPRO_BUNDLE_REQUIRED_FIELDS = ("
        "'schema_version', 'created_at', 'session_summary', 'failure_context', "
        "'changed_files', 'diff_stat', 'last_check_status', 'last_nudge_status', "
        "'next_agent_entrypoint', 'git_branch', 'git_head')\n"
    )
    write_text(
        tmp_path / "scripts" / "agent_repro_bundle.py",
        fields + "def write_bundle(): return 'manifest.json README.md diff.patch'\n",
    )
    write_text(
        tmp_path / "Makefile",
        "repro-bundle:\n\t$(PYTHON) scripts/agent_repro_bundle.py --summary x\n",
    )

    violations = module.check_failed_turn_repro_bundle_contract(tmp_path)

    assert violations == []


def test_failed_turn_repro_bundle_contract_accepts_current_script() -> None:
    module = load_agent_harness_contract_module()

    assert module.check_failed_turn_repro_bundle_contract(Path(__file__).resolve().parents[1]) == []


def test_context_engineering_prompt_contract_requires_prompt_partial_and_wiring(
    tmp_path: Path,
) -> None:
    module = load_agent_harness_contract_module()

    checker = getattr(module, "check_context_engineering_prompt_contract", None)
    assert checker is not None
    violations = checker(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS010", ".github/prompts/drift-context-engineering.prompt.md")
    ]
    assert "context-engineering prompt" in violations[0].message
    assert "Shared Partial" in violations[0].remediation


def test_context_engineering_prompt_contract_accepts_expected_wiring(tmp_path: Path) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / ".github" / "prompts" / "drift-context-engineering.prompt.md",
        "# Drift Context Engineering\n"
        "- `.github/prompts/_partials/context-engineering-contract.md`\n"
        "- `drift-harness-engine.prompt.md`\n"
        "- `drift-context-engineering-followup.prompt.md`\n",
    )
    write_text(
        tmp_path / ".github" / "prompts" / "drift-context-engineering-followup.prompt.md",
        "# Drift Context Engineering Follow-up\n"
        "Setzt einen identifizierten Kontext-Gap direkt um.\n",
    )
    write_text(
        tmp_path / ".github" / "prompts" / "_partials" / "context-engineering-contract.md",
        "# Context Contract\n"
        "## Statischer Kontext\n"
        "## Dynamischer Kontext\n",
    )
    write_text(
        tmp_path / ".github" / "prompts" / "drift-harness-engine.prompt.md",
        "Verwandte Prompts: `drift-context-engineering.prompt.md`\n",
    )
    write_text(
        tmp_path / "docs" / "agent-harness-golden-principles.md",
        "| AH-GP-009 | Context contract | check | remediation |\n",
    )
    write_text(
        tmp_path / ".github" / "prompts" / "README.md",
        "| [drift-context-engineering](drift-context-engineering.prompt.md) | Zweck |\n"
        "| [drift-context-engineering-followup]("
        "drift-context-engineering-followup.prompt.md) | Zweck |\n",
    )

    assert module.check_context_engineering_prompt_contract(tmp_path) == []


def test_followup_architecture_constraints_contract_requires_mechanical_rules(
    tmp_path: Path,
) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / ".github" / "prompts" / "drift-harness-followup.prompt.md",
        "# Drift Harness Follow-up\nArchitekturgrenzen sind wichtig.\n",
    )
    write_text(
        tmp_path / "docs" / "agent-harness-golden-principles.md",
        "| AH-GP-009 | Context contract | check | remediation |\n",
    )

    violations = module.check_followup_architecture_constraints_contract(tmp_path)

    assert [(item.code, item.path) for item in violations] == [
        ("HARNESS011", ".github/prompts/drift-harness-followup.prompt.md")
    ]
    assert "architecture layer chain" in violations[0].message
    assert "AH-GP-010" in violations[0].message


def test_followup_architecture_constraints_contract_accepts_mechanical_rules(
    tmp_path: Path,
) -> None:
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / ".github" / "prompts" / "drift-harness-followup.prompt.md",
        "# Drift Harness Follow-up\n"
        "Types -> Config -> Repo -> Service -> Runtime -> UI\n"
        "Jede Schicht darf nur aus Schichten links von ihr importieren.\n"
        "Mechanische Durchsetzung: deterministische Linter, LLM-Auditor, "
        "Strukturtests, pre-commit und CI-Validierung.\n",
    )
    write_text(
        tmp_path / "docs" / "agent-harness-golden-principles.md",
        "| AH-GP-010 | Architecture constraints | check | remediation |\n",
    )

    assert module.check_followup_architecture_constraints_contract(tmp_path) == []


def test_gate_status_persistence_fires_when_gate_check_missing(tmp_path: Path) -> None:
    """HARNESS012 must fire when scripts/gate_check.py does not exist."""
    module = load_agent_harness_contract_module()
    violations = module.check_gate_status_persistence(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS012"
    assert "missing" in violations[0].message.lower()


def test_gate_status_persistence_fires_when_marker_absent(tmp_path: Path) -> None:
    """HARNESS012 must fire when gate_check.py exists but lacks the status path."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "scripts" / "gate_check.py",
        "# gate_check stub without persistence\ndef main(): pass\n",
    )
    violations = module.check_gate_status_persistence(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS012"
    assert "last_gate_status.json" in violations[0].message


def test_gate_status_persistence_fires_when_status_artifact_missing(tmp_path: Path) -> None:
    """HARNESS012 must fire when the persisted gate-status JSON is missing."""
    module = load_agent_harness_contract_module()
    _gate_check_stub = (
        '# gate_check stub\n'
        'GATE_STATUS_PATH = REPO_ROOT / "work_artifacts" / "last_gate_status.json"\n'
    )
    write_text(tmp_path / "scripts" / "gate_check.py", _gate_check_stub)

    violations = module.check_gate_status_persistence(tmp_path)

    assert len(violations) == 1
    assert violations[0].code == "HARNESS012"
    assert violations[0].path == "work_artifacts/last_gate_status.json"
    assert "missing" in violations[0].message.lower()


def test_gate_status_persistence_fires_when_resume_fields_missing(tmp_path: Path) -> None:
    """HARNESS012 must fire when the status JSON lacks freshness or pass/fail metadata."""
    module = load_agent_harness_contract_module()
    _gate_check_stub = (
        '# gate_check stub\n'
        'GATE_STATUS_PATH = REPO_ROOT / "work_artifacts" / "last_gate_status.json"\n'
    )
    write_text(tmp_path / "scripts" / "gate_check.py", _gate_check_stub)
    write_text(
        tmp_path / "work_artifacts" / "last_gate_status.json",
        json.dumps({"commit_type": "fix"}),
    )

    violations = module.check_gate_status_persistence(tmp_path)

    assert len(violations) == 1
    assert violations[0].code == "HARNESS012"
    assert "passed" in violations[0].message
    assert "timestamp/generated_at" in violations[0].message


def test_gate_status_persistence_accepts_gate_check_with_marker(tmp_path: Path) -> None:
    """HARNESS012 must NOT fire when marker and persisted resume fields exist."""
    module = load_agent_harness_contract_module()
    _gate_check_stub = (
        '# gate_check stub\n'
        'GATE_STATUS_PATH = REPO_ROOT / "work_artifacts" / "last_gate_status.json"\n'
    )
    write_text(tmp_path / "scripts" / "gate_check.py", _gate_check_stub)
    write_text(
        tmp_path / "work_artifacts" / "last_gate_status.json",
        json.dumps({"generated_at": "2026-04-30T00:00:00+00:00", "passed": True}),
    )
    assert module.check_gate_status_persistence(tmp_path) == []


def test_gate_status_persistence_accepts_current_script() -> None:
    """HARNESS012 must pass against the actual scripts/gate_check.py in this repo."""
    module = load_agent_harness_contract_module()
    repo_root = Path(__file__).resolve().parents[1]
    assert module.check_gate_status_persistence(repo_root) == []


def test_kpi_snapshot_freshness_fires_when_snapshot_missing(tmp_path: Path) -> None:
    """HARNESS013 must fire when benchmark_results/kpi_snapshot.json does not exist."""
    module = load_agent_harness_contract_module()
    violations = module.check_kpi_snapshot_freshness(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS013"
    assert "missing" in violations[0].message.lower()


def test_kpi_snapshot_freshness_fires_when_freshness_field_absent(tmp_path: Path) -> None:
    """HARNESS013 must fire when kpi_snapshot.json has no timestamp or generated_at field."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "benchmark_results" / "kpi_snapshot.json",
        json.dumps({"version": "1.0", "precision_recall": {}}),
    )
    violations = module.check_kpi_snapshot_freshness(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS013"
    assert "freshness field" in violations[0].message


def test_kpi_snapshot_freshness_accepts_snapshot_with_timestamp(tmp_path: Path) -> None:
    """HARNESS013 must NOT fire when kpi_snapshot.json contains a 'timestamp' field."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "benchmark_results" / "kpi_snapshot.json",
        json.dumps({"timestamp": "2026-04-30T00:00:00+00:00", "version": "2.39.1"}),
    )
    assert module.check_kpi_snapshot_freshness(tmp_path) == []


def test_kpi_snapshot_freshness_accepts_snapshot_with_generated_at(tmp_path: Path) -> None:
    """HARNESS013 must NOT fire when kpi_snapshot.json contains a 'generated_at' field."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "benchmark_results" / "kpi_snapshot.json",
        json.dumps({"generated_at": "2026-04-30T00:00:00+00:00", "precision_recall": {}}),
    )
    assert module.check_kpi_snapshot_freshness(tmp_path) == []


def test_kpi_snapshot_freshness_accepts_current_repo_snapshot() -> None:
    """HARNESS013 must pass against the actual benchmark_results/kpi_snapshot.json in this repo."""
    module = load_agent_harness_contract_module()
    repo_root = Path(__file__).resolve().parents[1]
    assert module.check_kpi_snapshot_freshness(repo_root) == []


# ---------------------------------------------------------------------------
# HARNESS014 — work_artifacts index script
# ---------------------------------------------------------------------------


def test_work_artifacts_index_script_fires_when_script_missing(tmp_path: Path) -> None:
    """HARNESS014 must fire when scripts/update_work_artifacts_index.py does not exist."""
    module = load_agent_harness_contract_module()
    violations = module.check_work_artifacts_index_script(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS014"
    assert "missing" in violations[0].message.lower()


def test_work_artifacts_index_script_fires_when_marker_absent(tmp_path: Path) -> None:
    """HARNESS014 must fire when the script exists but does not reference the index path."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "scripts" / "update_work_artifacts_index.py",
        "# stub script without index reference\ndef main(): pass\n",
    )
    violations = module.check_work_artifacts_index_script(tmp_path)
    assert len(violations) == 1
    assert violations[0].code == "HARNESS014"
    assert "work_artifacts/index.json" in violations[0].message


def test_work_artifacts_index_script_accepts_script_with_marker(tmp_path: Path) -> None:
    """HARNESS014 must NOT fire when the script references work_artifacts/index.json."""
    module = load_agent_harness_contract_module()
    write_text(
        tmp_path / "scripts" / "update_work_artifacts_index.py",
        'INDEX_PATH = WORK_ARTIFACTS_DIR / "index.json"  # work_artifacts/index.json\n',
    )
    assert module.check_work_artifacts_index_script(tmp_path) == []


def test_work_artifacts_index_script_accepts_current_repo() -> None:
    """HARNESS014 must pass against the actual scripts/update_work_artifacts_index.py."""
    module = load_agent_harness_contract_module()
    repo_root = Path(__file__).resolve().parents[1]
    assert module.check_work_artifacts_index_script(repo_root) == []
