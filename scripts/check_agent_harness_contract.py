#!/usr/bin/env python3
"""Check agent-harness navigation, audit artifacts, and MCP boundaries.

The check is intentionally narrow: it protects the files and dependency
directions that help agents enter, diagnose, and safely extend the harness.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

REQUIRED_PATHS: tuple[str, ...] = (
    "AGENTS.md",
    ".github/AGENTS.md",
    ".github/copilot-instructions.md",
    "DEVELOPER.md",
    "docs/guides/agent-workflow.md",
    "docs/agent-harness-golden-principles.md",
    "audit/harness-engine-audit.md",
    "audit/improvement-plan.md",
    "audit/change-log.md",
    "audit/follow-up.md",
    "audit/harness-tool-map.json",
)

# Modules that legitimately own MCP tool dispatch. The first import inside an
# @mcp.tool()-decorated function body that matches one of these prefixes is
# considered the tool's owner. Any tool whose body matches none of these is
# either inline business logic (a leak) or must be allowlisted explicitly in
# audit/harness-tool-map.json under "inline_allowed".
MCP_TOOL_OWNER_PREFIXES: tuple[str, ...] = (
    "drift.mcp_router_",
    "drift.mcp_legacy",
    "drift.mcp_orchestration",
    "drift.mcp_autopilot",
    "drift.mcp_catalog",
    "drift.mcp_utils",
    "drift.mcp_enrichment",
    "drift.mcp_instructions",
    "drift.retrieval.mcp",
)

TOOL_MAP_RELPATH = "audit/harness-tool-map.json"
MCP_SERVER_RELPATH = "src/drift/mcp_server.py"

ROOT_ALLOWLIST_REQUIRED_ENTRIES: tuple[str, ...] = ("AGENTS.md", "audit")

AB_HARNESS_TARGET_RELPATH = "Makefile"
AB_HARNESS_TARGET_NAME = "ab-harness"

CONTEXT_ENGINEERING_PROMPT_RELPATH = ".github/prompts/drift-context-engineering.prompt.md"
CONTEXT_ENGINEERING_FOLLOWUP_PROMPT_RELPATH = (
    ".github/prompts/drift-context-engineering-followup.prompt.md"
)
CONTEXT_ENGINEERING_PARTIAL_RELPATH = (
    ".github/prompts/_partials/context-engineering-contract.md"
)
HARNESS_ENGINE_PROMPT_RELPATH = ".github/prompts/drift-harness-engine.prompt.md"
HARNESS_FOLLOWUP_PROMPT_RELPATH = ".github/prompts/drift-harness-followup.prompt.md"
PROMPTS_README_RELPATH = ".github/prompts/README.md"
GOLDEN_PRINCIPLES_RELPATH = "docs/agent-harness-golden-principles.md"

ARCHITECTURE_LAYER_SEQUENCE = "Types -> Config -> Repo -> Service -> Runtime -> UI"
ARCHITECTURE_ENFORCEMENT_TERMS: tuple[str, ...] = (
    "deterministische Linter",
    "LLM-Auditor",
    "Strukturtests",
    "pre-commit",
    "CI-Validierung",
)

REPRO_BUNDLE_SCRIPT_RELPATH = "scripts/agent_repro_bundle.py"
GATE_CHECK_SCRIPT_RELPATH = "scripts/gate_check.py"
GATE_STATUS_MARKER = "last_gate_status.json"
GATE_STATUS_RELPATH = "work_artifacts/last_gate_status.json"
GATE_STATUS_FRESHNESS_FIELDS: tuple[str, ...] = ("timestamp", "generated_at")
WORK_ARTIFACTS_INDEX_SCRIPT_RELPATH = "scripts/update_work_artifacts_index.py"
WORK_ARTIFACTS_INDEX_MARKER = "work_artifacts/index.json"
KPI_SNAPSHOT_RELPATH = "benchmark_results/kpi_snapshot.json"
KPI_SNAPSHOT_FRESHNESS_FIELDS: tuple[str, ...] = ("timestamp", "generated_at")
REPRO_BUNDLE_MAKE_TARGET = "repro-bundle"
REPRO_BUNDLE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "created_at",
    "session_summary",
    "failure_context",
    "changed_files",
    "diff_stat",
    "last_check_status",
    "last_nudge_status",
    "next_agent_entrypoint",
    "git_branch",
    "git_head",
)
REPRO_BUNDLE_REQUIRED_OUTPUTS: tuple[str, ...] = (
    "manifest.json",
    "README.md",
    "diff.patch",
)

MARKDOWN_DOCS: tuple[str, ...] = (
    "AGENTS.md",
    "docs/agent-harness-golden-principles.md",
    "audit/harness-engine-audit.md",
    "audit/improvement-plan.md",
    "audit/change-log.md",
    "audit/follow-up.md",
)

_LOCAL_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_SERVER_FORBIDDEN_IMPORT_RE = re.compile(
    r"^(?:from|import)\s+drift\.(?:api|analyzer|commands|ingestion|output|scoring|signals)\b"
)


@dataclass(frozen=True)
class Violation:
    code: str
    path: str
    message: str
    remediation: str


def _as_posix(path: str | Path) -> str:
    return Path(path).as_posix()


def _read_allowlist(path: Path) -> set[str]:
    entries: set[str] = set()
    if not path.exists():
        return entries
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            entries.add(line)
    return entries


def check_required_paths(
    repo_root: Path,
    *,
    required_paths: Sequence[str] = REQUIRED_PATHS,
) -> list[Violation]:
    violations: list[Violation] = []
    for required_path in required_paths:
        if not (repo_root / required_path).exists():
            violations.append(
                Violation(
                    code="HARNESS001",
                    path=required_path,
                    message=f"Required agent-harness artifact is missing: {required_path}",
                    remediation=(
                        f"Create {required_path} or remove it from REQUIRED_PATHS "
                        "with a reviewed replacement path."
                    ),
                )
            )
    return violations


def check_root_allowlist_entries(
    repo_root: Path,
    *,
    required_entries: Sequence[str] = ROOT_ALLOWLIST_REQUIRED_ENTRIES,
) -> list[Violation]:
    allowlist_path = repo_root / ".github" / "repo-root-allowlist"
    entries = _read_allowlist(allowlist_path)
    missing = [entry for entry in required_entries if entry not in entries]
    if not missing:
        return []
    return [
        Violation(
            code="HARNESS002",
            path=".github/repo-root-allowlist",
            message=(
                "Root allowlist is missing agent-harness entries: "
                + ", ".join(missing)
            ),
            remediation=(
                "Add the missing root entries so scripts/check_repo_hygiene.py "
                "accepts the versioned harness map and audit directory."
            ),
        )
    ]


def _extract_local_markdown_links(text: str) -> list[str]:
    links: list[str] = []
    for match in _LOCAL_LINK_RE.finditer(text):
        target = match.group(1).strip()
        if not target or target.startswith("#"):
            continue
        if "://" in target or target.startswith(("mailto:", "vscode:", "file:")):
            continue
        target = target.strip("<>").split()[0]
        if not target or target.startswith("#"):
            continue
        links.append(target)
    return links


def _resolve_markdown_target(repo_root: Path, doc_path: Path, target: str) -> Path:
    target_no_fragment = target.split("#", 1)[0].split("?", 1)[0]
    decoded = unquote(target_no_fragment)
    return (doc_path.parent / decoded).resolve()


def check_markdown_local_links(
    repo_root: Path,
    *,
    docs: Sequence[str] = MARKDOWN_DOCS,
) -> list[Violation]:
    violations: list[Violation] = []
    repo_root = repo_root.resolve()
    for doc in docs:
        doc_path = repo_root / doc
        if not doc_path.exists():
            continue
        text = doc_path.read_text(encoding="utf-8")
        missing_targets: list[str] = []
        for link_target in _extract_local_markdown_links(text):
            resolved = _resolve_markdown_target(repo_root, doc_path, link_target)
            if not resolved.exists():
                missing_targets.append(link_target)
        if missing_targets:
            violations.append(
                Violation(
                    code="HARNESS003",
                    path=doc,
                    message=(
                        "Missing local Markdown link target(s): "
                        + ", ".join(sorted(set(missing_targets)))
                    ),
                    remediation="Fix the link target or create the referenced document.",
                )
            )
    return violations


def check_mcp_boundary_contract(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    mcp_server_path = repo_root / "src" / "drift" / "mcp_server.py"
    if mcp_server_path.exists():
        for line_number, line in enumerate(
            mcp_server_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if _SERVER_FORBIDDEN_IMPORT_RE.search(line):
                violations.append(
                    Violation(
                        code="HARNESS005",
                        path="src/drift/mcp_server.py",
                        message=(
                            "mcp_server.py must remain a registration shell; "
                            f"business-logic import found on line {line_number}: {line.strip()}"
                        ),
                        remediation=(
                            "Move analysis/session/business logic into a "
                            "src/drift/mcp_router_*.py module and import that router instead."
                        ),
                    )
                )

    router_root = repo_root / "src" / "drift"
    for router_path in sorted(router_root.glob("mcp_router_*.py")):
        relative_router = _as_posix(router_path.relative_to(repo_root))
        for line_number, line in enumerate(
            router_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            stripped = line.strip()
            if stripped.startswith("from drift.mcp_server") or stripped.startswith(
                "import drift.mcp_server"
            ):
                violations.append(
                    Violation(
                        code="HARNESS004",
                        path=relative_router,
                        message=(
                            "MCP router modules must not import drift.mcp_server "
                            f"(line {line_number}: {stripped})."
                        ),
                        remediation=(
                            "Move shared helpers to mcp_utils, mcp_orchestration, "
                            "or a router-local helper to keep registration and logic acyclic."
                        ),
                    )
                )
    return violations


def parse_mcp_tools_from_server(repo_root: Path) -> list[dict[str, object]]:
    """AST-walk mcp_server.py and list every ``@mcp.tool()``-decorated function.

    Returns ordered entries ``{name, lineno, owner}`` where ``owner`` is the
    fully-qualified module name of the first import inside the function body
    that matches :data:`MCP_TOOL_OWNER_PREFIXES`, or ``None`` if no such import
    exists. Order matches source order so the generated JSON map is stable.
    """
    server_path = repo_root / MCP_SERVER_RELPATH
    if not server_path.exists():
        return []
    tree = ast.parse(server_path.read_text(encoding="utf-8"), filename=str(server_path))
    entries: list[dict[str, object]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if not _has_mcp_tool_decorator(node):
            continue
        owner = _first_router_owner(node.body)
        entries.append({"name": node.name, "lineno": node.lineno, "owner": owner})
    def _sort_key(item: dict[str, object]) -> tuple[int, str]:
        lineno = item.get("lineno", 0)
        name = item.get("name", "")
        return (int(lineno) if isinstance(lineno, int) else 0, str(name))

    entries.sort(key=_sort_key)
    return entries


def _has_mcp_tool_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for decorator in node.decorator_list:
        # Match ``@mcp.tool()`` or ``@mcp.tool(...)`` exactly.
        call = decorator if isinstance(decorator, ast.Call) else None
        if call is None:
            continue
        target = call.func
        if (
            isinstance(target, ast.Attribute)
            and target.attr == "tool"
            and isinstance(target.value, ast.Name)
            and target.value.id == "mcp"
        ):
            return True
    return False


def _first_router_owner(body: Sequence[ast.stmt]) -> str | None:
    for stmt in ast.walk(ast.Module(body=list(body), type_ignores=[])):
        if isinstance(stmt, ast.ImportFrom) and stmt.module:
            module = stmt.module
        elif isinstance(stmt, ast.Import):
            module = stmt.names[0].name if stmt.names else ""
        else:
            continue
        for prefix in MCP_TOOL_OWNER_PREFIXES:
            if module == prefix or module.startswith(prefix):
                return module
    return None


def _load_tool_map(repo_root: Path) -> dict[str, object]:
    path = repo_root / TOOL_MAP_RELPATH
    if not path.exists():
        return {"version": 1, "tools": [], "inline_allowed": []}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "tools": [], "inline_allowed": [], "_parse_error": True}
    if isinstance(loaded, dict):
        return dict(loaded)
    return {"version": 1, "tools": [], "inline_allowed": []}


def build_tool_map(repo_root: Path, *, inline_allowed: Sequence[str] = ()) -> dict[str, object]:
    """Build the canonical tool-map JSON structure from current source."""
    return {
        "version": 1,
        "tools": parse_mcp_tools_from_server(repo_root),
        "inline_allowed": sorted(set(inline_allowed)),
    }


def _format_tool_map(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, sort_keys=False) + "\n"


def write_tool_map(repo_root: Path) -> Path:
    """Regenerate audit/harness-tool-map.json, preserving inline_allowed entries."""
    existing = _load_tool_map(repo_root)
    inline_allowed = existing.get("inline_allowed", [])
    if not isinstance(inline_allowed, list):
        inline_allowed = []
    payload = build_tool_map(repo_root, inline_allowed=inline_allowed)
    target = repo_root / TOOL_MAP_RELPATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_format_tool_map(payload), encoding="utf-8")
    return target


def check_mcp_tool_router_ownership(repo_root: Path) -> list[Violation]:
    """Enforce that every registered MCP tool maps to a router/owner module.

    Two invariants are checked:
    - HARNESS006: ``audit/harness-tool-map.json`` is in sync with the actual
      ``@mcp.tool()`` registrations in ``mcp_server.py``.
    - HARNESS007: every registered tool has a router owner, unless its name
      is explicitly listed under ``inline_allowed`` in the tool map.
    """
    server_path = repo_root / MCP_SERVER_RELPATH
    if not server_path.exists():
        return []
    actual = parse_mcp_tools_from_server(repo_root)
    committed = _load_tool_map(repo_root)
    inline_allowed_raw = committed.get("inline_allowed", [])
    inline_allowed: set[str] = set()
    if isinstance(inline_allowed_raw, list):
        inline_allowed = {str(name) for name in inline_allowed_raw}

    violations: list[Violation] = []

    expected_payload = build_tool_map(repo_root, inline_allowed=sorted(inline_allowed))
    committed_tools_raw = committed.get("tools", [])
    committed_tools: list[dict[str, object]] = (
        [entry for entry in committed_tools_raw if isinstance(entry, dict)]
        if isinstance(committed_tools_raw, list)
        else []
    )
    committed_payload = {
        "version": committed.get("version", 1),
        "tools": committed_tools,
        "inline_allowed": sorted(inline_allowed),
    }
    if _format_tool_map(committed_payload) != _format_tool_map(expected_payload):
        committed_names: set[str] = {
            str(entry.get("name", "")) for entry in committed_tools if entry.get("name")
        }
        actual_names = {str(entry["name"]) for entry in actual}
        added = sorted(actual_names - committed_names)
        removed = sorted(committed_names - actual_names)
        detail_parts: list[str] = []
        if added:
            detail_parts.append("added: " + ", ".join(str(name) for name in added))
        if removed:
            detail_parts.append("removed: " + ", ".join(str(name) for name in removed))
        if not detail_parts:
            detail_parts.append("owner or line-number drift")
        violations.append(
            Violation(
                code="HARNESS006",
                path=TOOL_MAP_RELPATH,
                message=(
                    "Tool map is out of sync with @mcp.tool() registrations ("
                    + "; ".join(detail_parts)
                    + ")."
                ),
                remediation=(
                    "Run `python scripts/check_agent_harness_contract.py "
                    "--write-tool-map` and review the diff before committing."
                ),
            )
        )

    for entry in actual:
        name = str(entry["name"])
        owner = entry["owner"]
        if owner is None and name not in inline_allowed:
            violations.append(
                Violation(
                    code="HARNESS007",
                    path=MCP_SERVER_RELPATH,
                    message=(
                        f"MCP tool '{name}' (line {entry['lineno']}) has no router owner: "
                        "its body never imports from a drift.mcp_* or drift.retrieval.mcp module."
                    ),
                    remediation=(
                        "Move the tool body into an mcp_router_*/mcp_utils helper and import "
                        "that owner, or add the tool name to 'inline_allowed' in "
                        f"{TOOL_MAP_RELPATH} with a one-line comment explaining the exception."
                    ),
                )
            )
    return violations


def _extract_make_target_body(text: str, target_name: str) -> list[str]:
    body: list[str] = []
    in_target = False
    for line in text.splitlines():
        if not in_target:
            if line.startswith(f"{target_name}:"):
                in_target = True
            continue
        if line and not line.startswith(("\t", " ")):
            break
        body.append(line)
    return body


def check_ab_harness_target_uses_neutral_mock(repo_root: Path) -> list[Violation]:
    makefile_path = repo_root / AB_HARNESS_TARGET_RELPATH
    if not makefile_path.exists():
        return []

    body = _extract_make_target_body(
        makefile_path.read_text(encoding="utf-8"),
        AB_HARNESS_TARGET_NAME,
    )
    run_lines = [line.strip() for line in body if "scripts/ab_harness.py run" in line]
    if run_lines and any("--mock-mode neutral" in line for line in run_lines):
        return []

    detail = (
        "does not pass --mock-mode neutral"
        if run_lines
        else "does not run scripts/ab_harness.py run"
    )
    return [
        Violation(
            code="HARNESS008",
            path=AB_HARNESS_TARGET_RELPATH,
            message=(
                f"Make target '{AB_HARNESS_TARGET_NAME}' {detail}. "
                "The repo-level A/B harness target must measure neutral mock behavior; "
                "biased mock mode is only for explicit compatibility runs."
            ),
            remediation=(
                "Change the target to `$(PYTHON) scripts/ab_harness.py run "
                "--mock-mode neutral` and keep report metadata in sync."
            ),
        )
    ]


def _extract_string_sequence_assignment(source: str, assignment_name: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    for node in tree.body:
        if not isinstance(node, ast.Assign | ast.AnnAssign):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == assignment_name for target in targets
        ):
            continue
        value = node.value
        if not isinstance(value, ast.Tuple | ast.List | ast.Set):
            return set()
        values: set[str] = set()
        for item in value.elts:
            if isinstance(item, ast.Constant) and isinstance(item.value, str):
                values.add(item.value)
        return values
    return set()


def check_failed_turn_repro_bundle_contract(repo_root: Path) -> list[Violation]:
    script_path = repo_root / REPRO_BUNDLE_SCRIPT_RELPATH
    if not script_path.exists():
        return [
            Violation(
                code="HARNESS009",
                path=REPRO_BUNDLE_SCRIPT_RELPATH,
                message=(
                    "Missing failed agent-turn repro bundle script. "
                    "Failed turns need a compact repo-local export path."
                ),
                remediation=(
                    "Create scripts/agent_repro_bundle.py so a later agent can inspect "
                    "manifest.json, README.md, and diff.patch without terminal archaeology."
                ),
            )
        ]

    source = script_path.read_text(encoding="utf-8")
    declared_fields = _extract_string_sequence_assignment(source, "REPRO_BUNDLE_REQUIRED_FIELDS")
    missing_fields = sorted(set(REPRO_BUNDLE_REQUIRED_FIELDS) - declared_fields)
    missing_outputs = sorted(name for name in REPRO_BUNDLE_REQUIRED_OUTPUTS if name not in source)
    if not missing_fields and not missing_outputs:
        pass  # continue to Makefile check
    else:
        details: list[str] = []
        if missing_fields:
            details.append("missing manifest fields: " + ", ".join(missing_fields))
        if missing_outputs:
            details.append("missing bundle outputs: " + ", ".join(missing_outputs))

        return [
            Violation(
                code="HARNESS009",
                path=REPRO_BUNDLE_SCRIPT_RELPATH,
                message=(
                    "Failed agent-turn repro bundle contract is incomplete ("
                    + "; ".join(details)
                    + ")."
                ),
                remediation=(
                    "Keep scripts/agent_repro_bundle.py able to write a compact README.md, "
                    "manifest.json, and diff.patch with summary, failure context, changed files, "
                    "last check/nudge status, and a next-agent entry point."
                ),
            )
        ]

    # Check that a Makefile target exposes the bundle as a standard workflow entry point.
    makefile_path = repo_root / "Makefile"
    if not makefile_path.exists() or REPRO_BUNDLE_MAKE_TARGET not in makefile_path.read_text(
        encoding="utf-8"
    ):
        return [
            Violation(
                code="HARNESS009",
                path="Makefile",
                message=(
                    f"Missing '{REPRO_BUNDLE_MAKE_TARGET}' Make target. "
                    "A later agent cannot call the repro-bundle script via a standard "
                    "workflow entry point without it."
                ),
                remediation=(
                    f"Add a '{REPRO_BUNDLE_MAKE_TARGET}:' target to Makefile that calls "
                    "scripts/agent_repro_bundle.py with at least --summary, "
                    "--failure-context, --last-check-status, and --next-agent-entrypoint."
                ),
            )
        ]

    return []


def check_context_engineering_prompt_contract(repo_root: Path) -> list[Violation]:
    prompt_path = repo_root / CONTEXT_ENGINEERING_PROMPT_RELPATH
    partial_path = repo_root / CONTEXT_ENGINEERING_PARTIAL_RELPATH
    harness_engine_path = repo_root / HARNESS_ENGINE_PROMPT_RELPATH
    prompts_readme_path = repo_root / PROMPTS_README_RELPATH
    principles_path = repo_root / GOLDEN_PRINCIPLES_RELPATH

    problems: list[str] = []
    if not prompt_path.exists():
        problems.append(f"missing prompt: {CONTEXT_ENGINEERING_PROMPT_RELPATH}")
    if not partial_path.exists():
        problems.append(f"missing Shared Partial: {CONTEXT_ENGINEERING_PARTIAL_RELPATH}")
    if not harness_engine_path.exists():
        problems.append(f"missing harness prompt: {HARNESS_ENGINE_PROMPT_RELPATH}")
    if not prompts_readme_path.exists():
        problems.append(f"missing prompt catalog: {PROMPTS_README_RELPATH}")
    if not principles_path.exists():
        problems.append(f"missing principles doc: {GOLDEN_PRINCIPLES_RELPATH}")

    if not problems and partial_path.exists():
        partial_text = partial_path.read_text(encoding="utf-8")
        if "Statischer Kontext" not in partial_text:
            problems.append("partial does not define static context")
        if "Dynamischer Kontext" not in partial_text:
            problems.append("partial does not define dynamic context")

    if not problems and prompt_path.exists():
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if CONTEXT_ENGINEERING_PARTIAL_RELPATH not in prompt_text:
            problems.append("prompt does not reference the Shared Partial")
        if "drift-harness-engine.prompt.md" not in prompt_text:
            problems.append("prompt does not reference drift-harness-engine.prompt.md")

    if not problems and harness_engine_path.exists():
        harness_text = harness_engine_path.read_text(encoding="utf-8")
        if "drift-context-engineering.prompt.md" not in harness_text:
            problems.append("harness engine prompt does not link the context-engineering prompt")

    if not problems and prompts_readme_path.exists():
        readme_text = prompts_readme_path.read_text(encoding="utf-8")
        if "drift-context-engineering" not in readme_text:
            problems.append("prompt catalog does not list drift-context-engineering")
        if "drift-context-engineering-followup" not in readme_text:
            problems.append("prompt catalog does not list drift-context-engineering-followup")

    followup_path = repo_root / CONTEXT_ENGINEERING_FOLLOWUP_PROMPT_RELPATH
    if not followup_path.exists():
        problems.append(
            f"missing follow-up prompt: {CONTEXT_ENGINEERING_FOLLOWUP_PROMPT_RELPATH}"
        )
    elif prompt_path.exists():
        prompt_text_ce = prompt_path.read_text(encoding="utf-8")
        if "drift-context-engineering-followup.prompt.md" not in prompt_text_ce:
            problems.append(
                "context-engineering prompt does not reference the follow-up prompt"
            )

    if not problems and principles_path.exists():
        principles_text = principles_path.read_text(encoding="utf-8")
        if "AH-GP-009" not in principles_text:
            problems.append("golden principles do not record AH-GP-009")

    if not problems:
        return []

    return [
        Violation(
            code="HARNESS010",
            path=CONTEXT_ENGINEERING_PROMPT_RELPATH,
            message=(
                "The context-engineering prompt contract is incomplete ("
                + "; ".join(problems)
                + ")."
            ),
            remediation=(
                "Add the dedicated context-engineering prompt, its Shared Partial, "
                "the harness-engine and prompt-catalog wiring, and record AH-GP-009 "
                "in the golden principles."
            ),
        )
    ]


def check_gate_status_persistence(repo_root: Path) -> list[Violation]:
    """HARNESS012: gate_check.py must persist last_gate_status.json.

    An agent resuming after a session handover must be able to determine
    whether the last ``make gate-check`` run passed without re-executing it.
    This check verifies both halves of that contract:

    1. ``scripts/gate_check.py`` contains the marker string
       ``last_gate_status.json``, which indicates it writes the status
       artefact to ``work_artifacts/last_gate_status.json``.
    2. The persisted JSON artefact exists and contains a machine-readable
       pass/fail field plus freshness metadata so later agents can judge
       whether it is still safe to trust.
    """
    gate_check_path = repo_root / GATE_CHECK_SCRIPT_RELPATH
    if not gate_check_path.exists():
        return [
            Violation(
                code="HARNESS012",
                path=GATE_CHECK_SCRIPT_RELPATH,
                message="scripts/gate_check.py is missing.",
                remediation="Restore scripts/gate_check.py with gate-status persistence logic.",
            )
        ]

    source = gate_check_path.read_text(encoding="utf-8")
    if GATE_STATUS_MARKER not in source:
        return [
            Violation(
                code="HARNESS012",
                path=GATE_CHECK_SCRIPT_RELPATH,
                message=(
                    "gate_check.py does not write work_artifacts/last_gate_status.json. "
                    "Agents cannot determine whether the last gate-check passed after a "
                    "session handover."
                ),
                remediation=(
                    "Add a _write_gate_status() call in gate_check.py that persists the "
                    "gate result as JSON to work_artifacts/last_gate_status.json."
                ),
            )
        ]

    status_path = repo_root / GATE_STATUS_RELPATH
    if not status_path.exists():
        return [
            Violation(
                code="HARNESS012",
                path=GATE_STATUS_RELPATH,
                message=(
                    "work_artifacts/last_gate_status.json is missing. Agents cannot "
                    "inspect the most recent gate-check result after a session handover."
                ),
                remediation=(
                    "Run `make gate-check COMMIT_TYPE=<feat|fix|chore|signal>` so "
                    "scripts/gate_check.py writes work_artifacts/last_gate_status.json."
                ),
            )
        ]

    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return [
            Violation(
                code="HARNESS012",
                path=GATE_STATUS_RELPATH,
                message=(
                    "work_artifacts/last_gate_status.json is not valid JSON. Agents "
                    "cannot safely resume from a corrupted gate-status artefact."
                ),
                remediation=(
                    "Re-run make gate-check to regenerate a valid "
                    "work_artifacts/last_gate_status.json file."
                ),
            )
        ]

    missing_fields: list[str] = []
    if not any(field in payload for field in GATE_STATUS_FRESHNESS_FIELDS):
        missing_fields.append("timestamp/generated_at")
    if "passed" not in payload:
        missing_fields.append("passed")

    if missing_fields:
        return [
            Violation(
                code="HARNESS012",
                path=GATE_STATUS_RELPATH,
                message=(
                    "work_artifacts/last_gate_status.json is missing required "
                    f"resume fields: {', '.join(missing_fields)}."
                ),
                remediation=(
                    "Ensure scripts/gate_check.py persists both a boolean `passed` "
                    "field and freshness metadata (`generated_at` or `timestamp`) in "
                    "work_artifacts/last_gate_status.json, then regenerate the file."
                ),
            )
        ]
    return []


def check_kpi_snapshot_freshness(repo_root: Path) -> list[Violation]:
    """HARNESS013: benchmark_results/kpi_snapshot.json must carry a freshness field.

    Agents that rely on benchmark data to make decisions must be able to
    determine how old the snapshot is without running a full benchmark pass.
    This check verifies that ``benchmark_results/kpi_snapshot.json`` exists
    and contains at least one of the recognised freshness keys
    (``timestamp`` or ``generated_at``) so that staleness is always
    machine-readable.
    """
    snapshot_path = repo_root / KPI_SNAPSHOT_RELPATH
    if not snapshot_path.exists():
        return [
            Violation(
                code="HARNESS013",
                path=KPI_SNAPSHOT_RELPATH,
                message=(
                    "benchmark_results/kpi_snapshot.json is missing. "
                    "Agents cannot verify benchmark freshness."
                ),
                remediation=(
                    "Run the benchmark pipeline to regenerate "
                    "benchmark_results/kpi_snapshot.json."
                ),
            )
        ]

    try:
        data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [
            Violation(
                code="HARNESS013",
                path=KPI_SNAPSHOT_RELPATH,
                message="benchmark_results/kpi_snapshot.json is not valid JSON.",
                remediation="Regenerate the snapshot with the benchmark pipeline.",
            )
        ]

    if not any(field in data for field in KPI_SNAPSHOT_FRESHNESS_FIELDS):
        return [
            Violation(
                code="HARNESS013",
                path=KPI_SNAPSHOT_RELPATH,
                message=(
                    "benchmark_results/kpi_snapshot.json has no freshness field "
                    f"({', '.join(KPI_SNAPSHOT_FRESHNESS_FIELDS)}). "
                    "Agents cannot determine when the snapshot was generated."
                ),
                remediation=(
                    "Add a 'timestamp' or 'generated_at' ISO-8601 field to the "
                    "kpi_snapshot.json generation script."
                ),
            )
        ]
    return []


def check_work_artifacts_index_script(repo_root: Path) -> list[Violation]:
    """HARNESS014: scripts/update_work_artifacts_index.py must exist and target the index.

    Agents that resume after a session handover need a machine-readable index
    of ``work_artifacts/`` rather than a raw directory scan.  This check
    verifies that ``scripts/update_work_artifacts_index.py`` exists and
    contains the marker string ``work_artifacts/index.json``, which confirms
    it writes the index artefact that enables navigation without archaeology.
    """
    script_path = repo_root / WORK_ARTIFACTS_INDEX_SCRIPT_RELPATH
    if not script_path.exists():
        return [
            Violation(
                code="HARNESS014",
                path=WORK_ARTIFACTS_INDEX_SCRIPT_RELPATH,
                message=(
                    "scripts/update_work_artifacts_index.py is missing. "
                    "Agents cannot regenerate the work_artifacts/index.json "
                    "navigation index."
                ),
                remediation=(
                    "Create scripts/update_work_artifacts_index.py that writes "
                    "work_artifacts/index.json with one entry per artefact "
                    "(path, type, created_at, is_dir)."
                ),
            )
        ]

    source = script_path.read_text(encoding="utf-8")
    if WORK_ARTIFACTS_INDEX_MARKER not in source:
        return [
            Violation(
                code="HARNESS014",
                path=WORK_ARTIFACTS_INDEX_SCRIPT_RELPATH,
                message=(
                    "scripts/update_work_artifacts_index.py does not reference "
                    "work_artifacts/index.json. Agents cannot determine whether "
                    "the script writes the navigation index."
                ),
                remediation=(
                    "Ensure update_work_artifacts_index.py writes its output to "
                    "work_artifacts/index.json and that the path string appears "
                    "in the source."
                ),
            )
        ]
    return []


def check_followup_architecture_constraints_contract(repo_root: Path) -> list[Violation]:
    prompt_path = repo_root / HARNESS_FOLLOWUP_PROMPT_RELPATH
    principles_path = repo_root / GOLDEN_PRINCIPLES_RELPATH
    problems: list[str] = []

    if not prompt_path.exists():
        problems.append(f"missing follow-up prompt: {HARNESS_FOLLOWUP_PROMPT_RELPATH}")
    else:
        prompt_text = prompt_path.read_text(encoding="utf-8")
        if ARCHITECTURE_LAYER_SEQUENCE not in prompt_text:
            problems.append("follow-up prompt does not define the architecture layer chain")
        if "nur aus Schichten links von ihr importieren" not in prompt_text:
            problems.append("follow-up prompt does not define the import direction rule")
        for term in ARCHITECTURE_ENFORCEMENT_TERMS:
            if term not in prompt_text:
                problems.append(f"follow-up prompt does not name {term}")

    if not principles_path.exists():
        problems.append(f"missing principles doc: {GOLDEN_PRINCIPLES_RELPATH}")
    else:
        principles_text = principles_path.read_text(encoding="utf-8")
        if "AH-GP-010" not in principles_text:
            problems.append("golden principles do not record AH-GP-010")

    if not problems:
        return []

    return [
        Violation(
            code="HARNESS011",
            path=HARNESS_FOLLOWUP_PROMPT_RELPATH,
            message=(
                "The harness follow-up prompt does not encode mechanical "
                "architecture constraints (" + "; ".join(problems) + ")."
            ),
            remediation=(
                "Define the layer chain, the leftward import rule, concrete "
                "mechanical enforcement surfaces, and record AH-GP-010 in the "
                "golden principles."
            ),
        )
    ]


def run_checks(repo_root: Path) -> list[Violation]:
    repo_root = repo_root.resolve()
    violations: list[Violation] = []
    violations.extend(check_required_paths(repo_root))
    violations.extend(check_root_allowlist_entries(repo_root))
    violations.extend(check_markdown_local_links(repo_root))
    violations.extend(check_mcp_boundary_contract(repo_root))
    violations.extend(check_mcp_tool_router_ownership(repo_root))
    violations.extend(check_ab_harness_target_uses_neutral_mock(repo_root))
    violations.extend(check_failed_turn_repro_bundle_contract(repo_root))
    violations.extend(check_context_engineering_prompt_contract(repo_root))
    violations.extend(check_followup_architecture_constraints_contract(repo_root))
    violations.extend(check_gate_status_persistence(repo_root))
    violations.extend(check_kpi_snapshot_freshness(repo_root))
    violations.extend(check_work_artifacts_index_script(repo_root))
    return violations


def format_violations(violations: Sequence[Violation]) -> str:
    if not violations:
        return "Agent harness contract: OK"

    lines = ["Agent harness contract: FAIL", ""]
    for violation in violations:
        lines.append(f"{violation.code} {violation.path}: {violation.message}")
        lines.append(f"  Remediation: {violation.remediation}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check Drift agent-harness docs, audit artifacts, and MCP boundaries."
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to check (default: current working directory).",
    )
    parser.add_argument(
        "--write-tool-map",
        action="store_true",
        help=(
            "Regenerate audit/harness-tool-map.json from the current state of "
            "src/drift/mcp_server.py and exit. Existing 'inline_allowed' "
            "entries are preserved."
        ),
    )
    args = parser.parse_args(argv)

    if args.write_tool_map:
        target = write_tool_map(Path(args.root))
        print(f"Wrote {target}")
        return 0

    violations = run_checks(Path(args.root))
    print(format_violations(violations))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
