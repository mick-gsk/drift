"""drift-kit bootstrap: scaffold prompt files, settings.json and .gitignore.

One-command setup that makes drift-kit's slash commands work in VS Code Copilot
Chat without any manual config. Designed to be idempotent: running it again
adds only what is missing and never overwrites user content.
"""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import NamedTuple

PROMPT_TEMPLATES: tuple[str, ...] = (
    "drift-fix-plan.prompt.md",
    "drift-export-report.prompt.md",
    "drift-auto-fix-loop.prompt.md",
    "drift-feature-guardrails.prompt.md",
)

PROMPTS_DIR = Path(".github/prompts")
SETTINGS_FILE = Path(".vscode/settings.json")
GITIGNORE_FILE = Path(".gitignore")
SESSION_FILE_REL = ".vscode/drift-session.json"
SETTINGS_KEY = "chat.promptFilesLocations"
SETTINGS_VALUE = ".github/prompts/"

# Agent-target files
CURSOR_RULE_FILE = Path(".cursor/rules/drift.mdc")
CLAUDE_FILE = Path("CLAUDE.md")
AGENTS_FILE = Path("AGENTS.md")
_DRIFT_KIT_MARKER = "<!-- drift-kit -->"

_CURSOR_RULE_CONTENT = """\
---
description: Drift architectural analysis integration for Cursor
alwaysApply: false
---
# Drift Analysis Integration

After running `drift analyze`, read `.vscode/drift-session.json` for the current
architectural findings.

## Fix workflow
1. Read `top_findings` from `.vscode/drift-session.json`.
2. For each finding: show signal_type, severity, file_path, line_range, reason.
3. Propose a concrete code edit.
4. Ask the user: `Apply this fix? [yes / skip / stop]`

## Commands
- Run analysis: `drift analyze --repo . --exit-zero`
- Session file: `.vscode/drift-session.json`
"""

_DRIFT_KIT_AGENT_SECTION = """
<!-- drift-kit -->
## Drift-kit Integration

After running `drift analyze`, architectural findings are stored in
`.vscode/drift-session.json`. Use this file to generate fix plans, apply
targeted repairs, and assess risk before new features.

- **Run analysis**: `drift analyze --repo . --exit-zero`
- **Session file**: `.vscode/drift-session.json`
- **Fix workflow**: read `top_findings` -> propose edits -> apply with confirm/skip gates.
<!-- /drift-kit -->
"""


class InitResult(NamedTuple):
    """Result of a ``drift kit init`` run.

    Attributes
    ----------
    created:
        Workspace-relative paths of files that were newly created.
    updated:
        Workspace-relative paths of files that were modified in place
        (e.g. settings.json merge or .gitignore append).
    skipped:
        Workspace-relative paths of files left unchanged because they
        already contain the required content.
    agent_targets:
        Names of non-VS Code agent targets configured (cursor, claude, codex).
    """

    created: list[str]
    updated: list[str]
    skipped: list[str]
    agent_targets: tuple[str, ...] = ()


def _read_template(name: str) -> str:
    """Return the bundled prompt-file template content."""
    return (
        resources.files("drift.drift_kit.templates")
        .joinpath(name)
        .read_text(encoding="utf-8")
    )


def _write_prompts(repo: Path, *, force: bool) -> tuple[list[str], list[str]]:
    created: list[str] = []
    skipped: list[str] = []
    target_dir = repo / PROMPTS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in PROMPT_TEMPLATES:
        target = target_dir / name
        rel = str(target.relative_to(repo)).replace("\\", "/")
        if target.exists() and not force:
            skipped.append(rel)
            continue
        target.write_text(_read_template(name), encoding="utf-8")
        created.append(rel)
    return created, skipped


def _merge_settings(repo: Path) -> tuple[bool, bool]:
    """Merge ``chat.promptFilesLocations`` into ``.vscode/settings.json``.

    Returns ``(created, updated)`` flags. If the file did not exist it is
    created; if it existed but lacked the entry it is updated; if the entry
    was already present nothing changes and both flags are ``False``.
    """
    target = repo / SETTINGS_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(
            json.dumps({SETTINGS_KEY: [SETTINGS_VALUE]}, indent=2) + "\n",
            encoding="utf-8",
        )
        return True, False

    raw = target.read_text(encoding="utf-8")
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        # Don't clobber a settings.json with comments / trailing commas.
        return False, False
    if not isinstance(data, dict):
        return False, False

    locations = data.get(SETTINGS_KEY)
    if isinstance(locations, list) and SETTINGS_VALUE in locations:
        return False, False
    if isinstance(locations, list):
        locations.append(SETTINGS_VALUE)
    else:
        data[SETTINGS_KEY] = [SETTINGS_VALUE]
    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return False, True


def _append_gitignore(repo: Path) -> tuple[bool, bool]:
    """Ensure ``.vscode/drift-session.json`` is gitignored.

    Returns ``(created, updated)`` flags using the same semantics as
    :func:`_merge_settings`.
    """
    target = repo / GITIGNORE_FILE
    if not target.exists():
        target.write_text(
            "# Drift session context (drift-kit)\n" + SESSION_FILE_REL + "\n",
            encoding="utf-8",
        )
        return True, False
    content = target.read_text(encoding="utf-8")
    if SESSION_FILE_REL in content:
        return False, False
    suffix = "" if content.endswith("\n") else "\n"
    target.write_text(
        content + suffix + "\n# Drift session context (drift-kit)\n"
        + SESSION_FILE_REL + "\n",
        encoding="utf-8",
    )
    return False, True


def _write_cursor_rules(repo: Path, *, force: bool) -> tuple[bool, bool]:
    """Write ``.cursor/rules/drift.mdc``.

    Returns ``(created, updated)`` flags.
    """
    target = repo / CURSOR_RULE_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not force:
        return False, False
    existed = target.exists()
    target.write_text(_CURSOR_RULE_CONTENT, encoding="utf-8")
    return not existed, existed


def _append_agent_section(repo: Path, target_file: Path) -> tuple[bool, bool]:
    """Append a drift-kit section to *target_file* (e.g. CLAUDE.md or AGENTS.md).

    Returns ``(created, updated)`` flags. If the file did not exist it is
    created. If ``<!-- drift-kit -->`` is already present, nothing changes.
    """
    target = repo / target_file
    if not target.exists():
        target.write_text(_DRIFT_KIT_AGENT_SECTION.lstrip(), encoding="utf-8")
        return True, False
    content = target.read_text(encoding="utf-8")
    if _DRIFT_KIT_MARKER in content:
        return False, False
    suffix = "" if content.endswith("\n") else "\n"
    target.write_text(content + suffix + _DRIFT_KIT_AGENT_SECTION, encoding="utf-8")
    return False, True


def init_kit(
    repo: Path,
    *,
    force: bool = False,
    agents: tuple[str, ...] = (),
) -> InitResult:
    """Bootstrap drift-kit in *repo*.

    Writes the four slash-command prompt files into ``.github/prompts/``,
    ensures ``.vscode/settings.json`` exposes them via ``chat.promptFilesLocations``
    and adds ``.vscode/drift-session.json`` to ``.gitignore``.

    Pass ``agents`` to additionally configure non-VS Code agent targets:
    ``"cursor"`` writes ``.cursor/rules/drift.mdc``;
    ``"claude"`` appends a section to ``CLAUDE.md``;
    ``"codex"`` appends a section to ``AGENTS.md``;
    ``"all"`` does all of the above.

    The operation is idempotent: existing user content is preserved unless
    ``force`` is ``True`` (which only re-writes the prompt and cursor-rule files).
    """
    created, skipped = _write_prompts(repo, force=force)
    updated: list[str] = []

    settings_created, settings_updated = _merge_settings(repo)
    settings_rel = str(SETTINGS_FILE).replace("\\", "/")
    if settings_created:
        created.append(settings_rel)
    elif settings_updated:
        updated.append(settings_rel)
    else:
        skipped.append(settings_rel)

    gitignore_created, gitignore_updated = _append_gitignore(repo)
    gitignore_rel = str(GITIGNORE_FILE).replace("\\", "/")
    if gitignore_created:
        created.append(gitignore_rel)
    elif gitignore_updated:
        updated.append(gitignore_rel)
    else:
        skipped.append(gitignore_rel)

    active: set[str] = set(agents)
    agent_targets: list[str] = []

    if "cursor" in active or "all" in active:
        c_created, c_updated = _write_cursor_rules(repo, force=force)
        cursor_rel = str(CURSOR_RULE_FILE).replace("\\", "/")
        if c_created:
            created.append(cursor_rel)
        elif c_updated:
            updated.append(cursor_rel)
        else:
            skipped.append(cursor_rel)
        agent_targets.append("cursor")

    if "claude" in active or "all" in active:
        c_created, c_updated = _append_agent_section(repo, CLAUDE_FILE)
        claude_rel = str(CLAUDE_FILE).replace("\\", "/")
        if c_created:
            created.append(claude_rel)
        elif c_updated:
            updated.append(claude_rel)
        else:
            skipped.append(claude_rel)
        agent_targets.append("claude")

    if "codex" in active or "all" in active:
        c_created, c_updated = _append_agent_section(repo, AGENTS_FILE)
        codex_rel = str(AGENTS_FILE).replace("\\", "/")
        if c_created:
            created.append(codex_rel)
        elif c_updated:
            updated.append(codex_rel)
        else:
            skipped.append(codex_rel)
        agent_targets.append("codex")

    return InitResult(
        created=created,
        updated=updated,
        skipped=skipped,
        agent_targets=tuple(agent_targets),
    )
