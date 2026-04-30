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
