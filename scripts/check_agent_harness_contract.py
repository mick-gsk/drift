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


def run_checks(repo_root: Path) -> list[Violation]:
    repo_root = repo_root.resolve()
    violations: list[Violation] = []
    violations.extend(check_required_paths(repo_root))
    violations.extend(check_root_allowlist_entries(repo_root))
    violations.extend(check_markdown_local_links(repo_root))
    violations.extend(check_mcp_boundary_contract(repo_root))
    violations.extend(check_mcp_tool_router_ownership(repo_root))
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
