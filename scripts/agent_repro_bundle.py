#!/usr/bin/env python3
"""Create a compact repo-local bundle for a failed agent turn.

The bundle is intentionally small: a machine-readable manifest, a human entry
README, and an optional patch snapshot. It is meant for the next agent, not for
long-form audit prose.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "work_artifacts" / "repro_bundles"

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


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_command(cmd: list[str], *, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _git_branch() -> str:
    return _run_command(["git", "branch", "--show-current"]) or "unknown"


def _git_head() -> str:
    return _run_command(["git", "rev-parse", "--short", "HEAD"]) or "unknown"


def _git_diff_stat() -> str:
    return _run_command(["git", "diff", "--stat", "HEAD"]) or "(no diff stat captured)"


def _git_diff_patch() -> str:
    return _run_command(["git", "diff", "--binary", "HEAD"])


def _git_changed_files() -> list[str]:
    tracked = _run_command(["git", "diff", "--name-only", "HEAD"])
    untracked = _run_command(["git", "ls-files", "--others", "--exclude-standard"])
    files = [line.strip() for block in (tracked, untracked) for line in block.splitlines()]
    return sorted({item for item in files if item})


def make_bundle_id(raw_session_id: str | None = None) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d_%H%M%S")
    suffix = (raw_session_id or uuid.uuid4().hex)[:8]
    return f"{stamp}_{suffix}"


def build_bundle_payload(
    *,
    session_summary: str,
    failure_context: str,
    changed_files: list[str],
    diff_stat: str,
    last_check_status: str,
    last_nudge_status: str,
    next_agent_entrypoint: str,
    git_branch: str,
    git_head: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": 1,
        "created_at": created_at or _utc_now_iso(),
        "session_summary": session_summary.strip(),
        "failure_context": failure_context.strip(),
        "changed_files": list(changed_files),
        "diff_stat": diff_stat.strip() or "(no diff stat captured)",
        "last_check_status": last_check_status.strip(),
        "last_nudge_status": last_nudge_status.strip() or "(not recorded)",
        "next_agent_entrypoint": next_agent_entrypoint.strip(),
        "git_branch": git_branch.strip() or "unknown",
        "git_head": git_head.strip() or "unknown",
    }
    missing = [field for field in REPRO_BUNDLE_REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError("Missing repro bundle field(s): " + ", ".join(missing))
    return payload


def render_readme(payload: dict[str, Any], *, has_patch: bool) -> str:
    changed_files = payload.get("changed_files", [])
    changed_file_lines = "\n".join(f"- {path}" for path in changed_files) or "- (none captured)"
    patch_line = "- Diff snapshot: diff.patch" if has_patch else "- Diff snapshot: not captured"
    return (
        "# Failed Agent Turn Repro Bundle\n\n"
        "## Failed Turn Summary\n\n"
        f"{payload['session_summary']}\n\n"
        "## Failure Or Remediation Context\n\n"
        f"{payload['failure_context']}\n\n"
        "## Changed Files\n\n"
        f"{changed_file_lines}\n\n"
        "## Last Check Status\n\n"
        "```\n"
        f"{payload['last_check_status']}\n"
        "```\n\n"
        "## Last Nudge Or Diff Status\n\n"
        "```\n"
        f"{payload['last_nudge_status']}\n"
        "```\n\n"
        "## Next Agent Entry Point\n\n"
        f"{payload['next_agent_entrypoint']}\n\n"
        "## Bundle Files\n\n"
        "- Machine-readable manifest: manifest.json\n"
        f"{patch_line}\n"
    )


def write_bundle(
    payload: dict[str, Any],
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    bundle_id: str | None = None,
    diff_patch: str = "",
) -> Path:
    target = output_root / (bundle_id or make_bundle_id(str(payload.get("git_head", ""))))
    target.mkdir(parents=True, exist_ok=True)

    manifest_path = target / "manifest.json"
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    has_patch = bool(diff_patch.strip())
    readme_path = target / "README.md"
    readme_path.write_text(render_readme(payload, has_patch=has_patch), encoding="utf-8")

    if has_patch:
        (target / "diff.patch").write_text(diff_patch, encoding="utf-8")

    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a failed agent-turn repro bundle.")
    parser.add_argument("--summary", required=True, help="Short summary of the failed turn.")
    parser.add_argument(
        "--failure-context",
        required=True,
        help="Relevant error, blocker, or remediation context from the failed turn.",
    )
    parser.add_argument(
        "--last-check-status",
        required=True,
        help="Last meaningful check result, including command and status.",
    )
    parser.add_argument(
        "--last-nudge-status",
        default="",
        help="Last drift_nudge, drift_diff, or comparable status line.",
    )
    parser.add_argument(
        "--next-agent-entrypoint",
        required=True,
        help="First concrete step the next agent should take.",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Changed file to record. Repeatable; defaults to git-detected changes.",
    )
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional session or failure id used in the bundle directory suffix.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Directory under which the bundle directory is created.",
    )
    args = parser.parse_args()

    changed_files = args.changed_file or _git_changed_files()
    payload = build_bundle_payload(
        session_summary=args.summary,
        failure_context=args.failure_context,
        changed_files=changed_files,
        diff_stat=_git_diff_stat(),
        last_check_status=args.last_check_status,
        last_nudge_status=args.last_nudge_status,
        next_agent_entrypoint=args.next_agent_entrypoint,
        git_branch=_git_branch(),
        git_head=_git_head(),
    )
    output_path = write_bundle(
        payload,
        output_root=args.output_root,
        bundle_id=make_bundle_id(args.session_id or None),
        diff_patch=_git_diff_patch(),
    )
    if output_path.is_relative_to(REPO_ROOT):
        display_path = output_path.relative_to(REPO_ROOT)
    else:
        display_path = output_path
    print(display_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
