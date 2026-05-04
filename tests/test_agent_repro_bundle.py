from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agent_repro_bundle.py"


def load_repro_bundle_module() -> Any:
    spec = importlib.util.spec_from_file_location("agent_repro_bundle", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_repro_bundle"] = module
    spec.loader.exec_module(module)
    return module


def test_build_bundle_payload_contains_failed_turn_context() -> None:
    module = load_repro_bundle_module()

    payload = module.build_bundle_payload(
        session_summary="Tried to push harness branch after contract fix.",
        failure_context="git push failed on pre-push Gate 8.",
        changed_files=[
            "scripts/check_agent_harness_contract.py",
            "tests/test_agent_harness_contract.py",
        ],
        diff_stat="2 files changed, 40 insertions(+)",
        last_check_status="make agent-harness-check: OK",
        last_nudge_status="direction=stable safe_to_commit=true",
        next_agent_entrypoint="Run make gate-check COMMIT_TYPE=feat, then inspect Gate 8.",
        git_branch="feat/harness",
        git_head="abc1234",
    )

    assert payload["schema_version"] == 1
    assert payload["session_summary"].startswith("Tried to push")
    assert payload["failure_context"] == "git push failed on pre-push Gate 8."
    assert payload["changed_files"] == [
        "scripts/check_agent_harness_contract.py",
        "tests/test_agent_harness_contract.py",
    ]
    assert payload["last_check_status"] == "make agent-harness-check: OK"
    assert payload["last_nudge_status"] == "direction=stable safe_to_commit=true"
    assert payload["next_agent_entrypoint"].startswith("Run make gate-check")
    assert payload["git_branch"] == "feat/harness"
    assert payload["git_head"] == "abc1234"


def test_write_bundle_creates_manifest_readme_and_patch(tmp_path: Path) -> None:
    module = load_repro_bundle_module()
    payload = module.build_bundle_payload(
        session_summary="Failed harness follow-up turn.",
        failure_context="Targeted pytest failed on HARNESS009.",
        changed_files=["scripts/agent_repro_bundle.py"],
        diff_stat="1 file changed, 12 insertions(+)",
        last_check_status="pytest tests/test_agent_repro_bundle.py: failed",
        last_nudge_status="direction=stable safe_to_commit=true",
        next_agent_entrypoint="Open manifest.json, then run the listed pytest command.",
        git_branch="feat/harness",
        git_head="def5678",
    )

    bundle_dir = module.write_bundle(
        payload,
        output_root=tmp_path,
        bundle_id="20260430_120000_deadbeef",
        diff_patch="diff --git a/scripts/agent_repro_bundle.py b/scripts/agent_repro_bundle.py\n",
    )

    assert bundle_dir == tmp_path / "20260430_120000_deadbeef"
    manifest = json.loads((bundle_dir / "manifest.json").read_text(encoding="utf-8"))
    readme = (bundle_dir / "README.md").read_text(encoding="utf-8")
    patch = (bundle_dir / "diff.patch").read_text(encoding="utf-8")

    assert manifest["failure_context"] == "Targeted pytest failed on HARNESS009."
    assert manifest["changed_files"] == ["scripts/agent_repro_bundle.py"]
    assert "## Failed Turn Summary" in readme
    assert "## Next Agent Entry Point" in readme
    assert "manifest.json" in readme
    assert patch.startswith("diff --git")
