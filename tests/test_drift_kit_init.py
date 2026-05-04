"""Tests for ``drift kit init`` scaffolding."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner
from drift.cli import main
from drift.drift_kit._init import (
    AGENTS_FILE,
    CLAUDE_FILE,
    CURSOR_RULE_FILE,
    PROMPT_TEMPLATES,
    SETTINGS_KEY,
    SETTINGS_VALUE,
    init_kit,
)


def test_init_kit_creates_all_artifacts(tmp_path: Path) -> None:
    result = init_kit(tmp_path)

    for name in PROMPT_TEMPLATES:
        target = tmp_path / ".github/prompts" / name
        assert target.exists()
        assert target.read_text(encoding="utf-8").startswith("---\n")

    settings = json.loads((tmp_path / ".vscode/settings.json").read_text("utf-8"))
    assert SETTINGS_VALUE in settings[SETTINGS_KEY]

    gitignore = (tmp_path / ".gitignore").read_text("utf-8")
    assert ".vscode/drift-session.json" in gitignore

    assert any("drift-fix-plan" in p for p in result.created)
    assert ".vscode/settings.json" in result.created
    assert ".gitignore" in result.created


def test_init_kit_is_idempotent(tmp_path: Path) -> None:
    init_kit(tmp_path)
    second = init_kit(tmp_path)

    assert second.created == []
    assert second.updated == []
    # All artifacts now reported as skipped.
    assert any(name in p for p in second.skipped for name in PROMPT_TEMPLATES)
    assert ".vscode/settings.json" in second.skipped
    assert ".gitignore" in second.skipped


def test_init_kit_preserves_existing_settings(tmp_path: Path) -> None:
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    (vscode / "settings.json").write_text(
        json.dumps({"editor.tabSize": 4, SETTINGS_KEY: ["custom/path/"]}, indent=2),
        encoding="utf-8",
    )

    init_kit(tmp_path)

    settings = json.loads((vscode / "settings.json").read_text("utf-8"))
    assert settings["editor.tabSize"] == 4
    assert "custom/path/" in settings[SETTINGS_KEY]
    assert SETTINGS_VALUE in settings[SETTINGS_KEY]


def test_init_kit_does_not_duplicate_gitignore_entry(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text(
        "node_modules/\n.vscode/drift-session.json\n", encoding="utf-8"
    )

    init_kit(tmp_path)

    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert content.count(".vscode/drift-session.json") == 1


def test_init_kit_skips_existing_prompt_without_force(tmp_path: Path) -> None:
    prompts_dir = tmp_path / ".github/prompts"
    prompts_dir.mkdir(parents=True)
    custom = prompts_dir / "drift-fix-plan.prompt.md"
    custom.write_text("CUSTOM USER CONTENT", encoding="utf-8")

    init_kit(tmp_path)

    assert custom.read_text(encoding="utf-8") == "CUSTOM USER CONTENT"


def test_init_kit_force_overwrites_prompts(tmp_path: Path) -> None:
    prompts_dir = tmp_path / ".github/prompts"
    prompts_dir.mkdir(parents=True)
    custom = prompts_dir / "drift-fix-plan.prompt.md"
    custom.write_text("CUSTOM USER CONTENT", encoding="utf-8")

    init_kit(tmp_path, force=True)

    assert custom.read_text(encoding="utf-8").startswith("---\n")


def test_init_kit_handles_corrupt_settings_json(tmp_path: Path) -> None:
    vscode = tmp_path / ".vscode"
    vscode.mkdir()
    corrupt = vscode / "settings.json"
    # Settings.json with comments — invalid JSON, common in VS Code.
    corrupt.write_text('{\n  // comment\n  "a": 1\n}\n', encoding="utf-8")

    # Must not crash and must not clobber the file.
    result = init_kit(tmp_path)

    assert corrupt.read_text(encoding="utf-8").startswith("{\n  // comment")
    assert ".vscode/settings.json" in result.skipped


@pytest.mark.parametrize("flag", [[], ["--force"]])
def test_cli_kit_init(tmp_path: Path, flag: list[str]) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["kit", "init", "--repo", str(tmp_path), *flag])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".github/prompts/drift-fix-plan.prompt.md").exists()
    assert (tmp_path / ".vscode/settings.json").exists()
    assert "drift analyze" in result.output


# ---------------------------------------------------------------------------
# Phase C: drift-feature-guardrails template
# ---------------------------------------------------------------------------

def test_feature_guardrails_template_exists(tmp_path: Path) -> None:
    init_kit(tmp_path)
    f = tmp_path / ".github/prompts/drift-feature-guardrails.prompt.md"
    assert f.exists()
    assert f.read_text(encoding="utf-8").startswith("---\n")


# ---------------------------------------------------------------------------
# Phase B: --agent flag (cursor, claude, codex, all)
# ---------------------------------------------------------------------------

def test_init_kit_cursor_agent(tmp_path: Path) -> None:
    result = init_kit(tmp_path, agents=("cursor",))
    assert (tmp_path / CURSOR_RULE_FILE).exists()
    assert "cursor" in result.agent_targets


def test_init_kit_claude_agent(tmp_path: Path) -> None:
    result = init_kit(tmp_path, agents=("claude",))
    assert (tmp_path / CLAUDE_FILE).exists()
    content = (tmp_path / CLAUDE_FILE).read_text(encoding="utf-8")
    assert "<!-- drift-kit -->" in content
    assert "claude" in result.agent_targets


def test_init_kit_codex_agent(tmp_path: Path) -> None:
    result = init_kit(tmp_path, agents=("codex",))
    assert (tmp_path / AGENTS_FILE).exists()
    content = (tmp_path / AGENTS_FILE).read_text(encoding="utf-8")
    assert "<!-- drift-kit -->" in content
    assert "codex" in result.agent_targets


def test_init_kit_all_agents(tmp_path: Path) -> None:
    result = init_kit(tmp_path, agents=("all",))
    assert (tmp_path / CURSOR_RULE_FILE).exists()
    assert (tmp_path / CLAUDE_FILE).exists()
    assert (tmp_path / AGENTS_FILE).exists()
    assert set(result.agent_targets) == {"cursor", "claude", "codex"}


def test_init_kit_agent_section_idempotent_claude(tmp_path: Path) -> None:
    init_kit(tmp_path, agents=("claude",))
    init_kit(tmp_path, agents=("claude",))
    content = (tmp_path / CLAUDE_FILE).read_text(encoding="utf-8")
    assert content.count("<!-- drift-kit -->") == 1


def test_init_kit_agent_section_appends_to_existing_claude_md(tmp_path: Path) -> None:
    (tmp_path / CLAUDE_FILE).write_text("# Existing Content\n\nUser notes.\n", encoding="utf-8")
    init_kit(tmp_path, agents=("claude",))
    content = (tmp_path / CLAUDE_FILE).read_text(encoding="utf-8")
    assert "# Existing Content" in content
    assert "<!-- drift-kit -->" in content


def test_init_kit_no_agents_returns_empty_agent_targets(tmp_path: Path) -> None:
    result = init_kit(tmp_path)
    assert result.agent_targets == ()


def test_cli_kit_init_with_cursor(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["kit", "init", "--repo", str(tmp_path), "--agent", "cursor"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / CURSOR_RULE_FILE).exists()


def test_cli_kit_init_with_all_agents(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["kit", "init", "--repo", str(tmp_path), "--agent", "all"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / CURSOR_RULE_FILE).exists()
    assert (tmp_path / CLAUDE_FILE).exists()
    assert (tmp_path / AGENTS_FILE).exists()


# ---------------------------------------------------------------------------
# Phase A: --and-analyze flag
# ---------------------------------------------------------------------------

def test_cli_kit_init_and_analyze(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(cmd)

        class R:
            returncode = 0

        return R()  # type: ignore[return-value]

    monkeypatch.setattr(subprocess, "run", fake_run)

    runner = CliRunner()
    result = runner.invoke(main, ["kit", "init", "--repo", str(tmp_path), "--and-analyze"])
    assert result.exit_code == 0, result.output
    assert any("drift" in str(c) for c in calls)
