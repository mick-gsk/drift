"""Standalone MCP server for internal drift repo operations.

Exposes repo-internal tools that are NOT part of the public drift-analyzer package:
    drift_product_health      — PyPI/GitHub adoption + stability snapshot
    drift_release_readiness   — GO/NO-GO gate before pushing a release
    drift_working_tree_context — Current change set + triggered pre-push gates
    drift_audit_freshness     — §18 audit artefact staleness check

Register in .vscode/mcp.json:
    "drift-product-health": {
        "type": "stdio",
        "command": "<venv>/Scripts/python.exe",
        "args": ["scripts/mcp_product_health_server.py"]
    }
"""

from __future__ import annotations

import datetime
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

# ---- resolve repo root (two levels up from this script) ----
_REPO_ROOT = Path(__file__).resolve().parent.parent

try:
    from typing import Annotated

    from mcp.server.fastmcp import FastMCP
    from pydantic import Field
except ImportError:
    print(
        "Missing dependency: pip install 'drift-analyzer[mcp]'",
        file=sys.stderr,
    )
    sys.exit(1)

mcp = FastMCP("drift-repo-ops")

_SNAPSHOT_REL = "benchmark_results/kpi_snapshot.json"


def _read_snapshot(repo_root: Path) -> dict | None:
    path = repo_root / _SNAPSHOT_REL
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _snapshot_age(snapshot: dict) -> float | None:
    ts_raw = snapshot.get("timestamp")
    if not ts_raw:
        return None
    try:
        ts = datetime.datetime.fromisoformat(ts_raw)
        now = datetime.datetime.now(datetime.UTC)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=datetime.UTC)
        return (now - ts).total_seconds()
    except ValueError:
        return None


def _agent_instruction(ph: dict) -> str:
    adoption = ph.get("adoption", {})
    stability = ph.get("stability", {})
    mom = adoption.get("pypi_downloads_mom_delta")
    open_bugs = stability.get("open_bugs")
    headroom = (ph.get("performance") or {}).get("budget_headroom_pct")

    parts: list[str] = []
    if mom is not None and mom < -0.30:
        parts.append(
            f"ALARM: PyPI downloads dropped {mom * 100:.1f}% MoM — investigate urgently."
        )
    elif mom is not None and mom < -0.20:
        parts.append(
            f"WARNING: PyPI downloads dropped {mom * 100:.1f}% MoM — consider a release announcement."
        )
    if headroom is not None and headroom < 0.10:
        parts.append("ALARM: performance budget nearly exhausted.")
    elif headroom is not None and headroom < 0.30:
        parts.append("WARNING: performance budget headroom below 30%.")
    if open_bugs is not None and open_bugs > 5:
        parts.append(f"{open_bugs} open bugs — prioritise triage.")

    if not parts:
        parts.append("Product health is HEALTHY. No immediate action required.")

    return " ".join(parts)


@mcp.tool()
async def drift_product_health(
    refresh: Annotated[
        bool,
        Field(
            description=(
                "When True, fetch live data from PyPI and GitHub APIs instead of "
                "reading the cached benchmark_results/kpi_snapshot.json. "
                "Use sparingly — live fetches hit external APIs."
            )
        ),
    ] = False,
) -> str:
    """Return the current product health snapshot for the drift-analyzer package.

    Reads adoption metrics (PyPI downloads, MoM delta, GitHub stars/forks),
    stability (open issues, open bugs), and performance headroom from the
    cached benchmark_results/kpi_snapshot.json.

    Returns a JSON payload with keys:
      - ``source``: "snapshot" or "live"
      - ``snapshot_age_seconds``: seconds since the snapshot was collected (null if live)
      - ``adoption``: PyPI/GitHub metrics
      - ``stability``: open issue/bug counts
      - ``performance``: budget headroom
      - ``agent_instruction``: plain-text action recommendation

    Agents should call this weekly or when evaluating adoption trends.
    To refresh: set refresh=True. To update the cached snapshot run:
        python scripts/collect_kpi_snapshot.py --product-health
    """
    if not refresh:
        snapshot = _read_snapshot(_REPO_ROOT)
        if snapshot is not None:
            ph = snapshot.get("product_health")
            if ph is not None:
                age = _snapshot_age(snapshot)
                return json.dumps(
                    {
                        "source": "snapshot",
                        "snapshot_timestamp": snapshot.get("timestamp"),
                        "snapshot_age_seconds": age,
                        **ph,
                        "agent_instruction": _agent_instruction(ph),
                    },
                    default=str,
                )
        # No snapshot or no product_health section
        return json.dumps(
            {
                "source": "no_data",
                "error": (
                    "No product_health in kpi_snapshot.json. "
                    "Run: python scripts/collect_kpi_snapshot.py --product-health"
                ),
                "agent_instruction": (
                    "Run `python scripts/collect_kpi_snapshot.py --product-health` "
                    "to populate product health data, then call this tool again."
                ),
            }
        )

    # Live fetch
    scripts_dir = _REPO_ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))

    try:
        from collect_kpi_snapshot import collect_product_health  # type: ignore[import]

        ph = collect_product_health()
        return json.dumps(
            {
                "source": "live",
                "snapshot_age_seconds": None,
                **ph,
                "agent_instruction": _agent_instruction(ph),
            },
            default=str,
        )
    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "source": "live",
                "error": str(exc),
                "agent_instruction": f"Live fetch failed: {exc}. Check network access.",
            }
        )


# ---------------------------------------------------------------------------
# Shared helpers for release readiness / working-tree / audit tools
# ---------------------------------------------------------------------------

_RELEASE_HEADER_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]\s+[–-]\s+.+$", re.MULTILINE)
_SECTION_HEADER_RE = re.compile(r"^### (Added|Changed|Fixed)\s*$")
_CONVENTIONAL_RE = re.compile(
    r"^-\s+(feat|fix|docs|chore|refactor|perf|test|style|ci)(\(.+\))?:",
    re.IGNORECASE,
)
_AUDIT_FILES = [
    "fmea_matrix.md",
    "stride_threat_model.md",
    "risk_register.md",
    "fault_trees.md",
]


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_pyproject_version(repo_root: Path) -> str:
    with (repo_root / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)["project"]["version"]


def _extract_top_changelog(repo_root: Path) -> tuple[str, str]:
    """Return (version, body) of the topmost release section in CHANGELOG.md."""
    text = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
    matches = list(_RELEASE_HEADER_RE.finditer(text))
    if not matches:
        return "", ""
    first = matches[0]
    version = first.group(1)
    start = first.end()
    end = matches[1].start() if len(matches) > 1 else len(text)
    body = text[start:end].strip("\n")
    return version, body


def _changelog_blockers(version: str, body: str) -> list[str]:
    blockers: list[str] = []
    lines = [ln.rstrip() for ln in body.splitlines()]
    first_non_empty = next((ln.strip() for ln in lines if ln.strip()), None)
    if first_non_empty is None or not first_non_empty.startswith("Short version:"):
        blockers.append("CHANGELOG top entry is missing 'Short version:' summary line.")

    bullets: list[str] = []
    current_section: str | None = None
    for raw in body.splitlines():
        ln = raw.rstrip()
        m = _SECTION_HEADER_RE.match(ln.strip())
        if m:
            current_section = m.group(1)
            continue
        if ln.startswith("### "):
            current_section = None
            continue
        if current_section in {"Added", "Changed", "Fixed"} and ln.lstrip().startswith("- "):
            bullets.append(ln.lstrip())

    if not bullets:
        blockers.append("CHANGELOG top entry has no curated bullets under Added/Changed/Fixed.")
    if len(bullets) > 5:
        blockers.append(
            f"CHANGELOG top entry has {len(bullets)} bullets (max 5). Compress the entry."
        )
    for b in bullets:
        if _CONVENTIONAL_RE.match(b):
            blockers.append(f"CHANGELOG bullet is a raw conventional-commit message: {b!r}")
            break

    return blockers


# ---------------------------------------------------------------------------
# Tool: drift_release_readiness
# ---------------------------------------------------------------------------


@mcp.tool()
async def drift_release_readiness() -> str:  # type: ignore[empty-body]
    """Check whether the repo is in GO state for a release push.

    Validates:
    - pyproject.toml version matches top CHANGELOG entry
    - CHANGELOG top entry has 'Short version:' and curated bullets
    - SECURITY.md lists the current major.minor.x supported version line
    - llms.txt 'Release status:' matches the current version
    - blast_reports/ has a report for the current HEAD SHA (if src/drift changed)

    Returns JSON:
        {
            "version": "x.y.z",
            "status": "GO" | "NO_GO",
            "blockers": ["..."],
            "warnings": ["..."],
            "agent_instruction": "..."
        }
    """
    repo_root = _REPO_ROOT
    blockers: list[str] = []
    warnings: list[str] = []

    # 1. pyproject version
    try:
        version = _read_pyproject_version(repo_root)
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": f"Cannot read pyproject.toml: {exc}"})

    # 2. CHANGELOG top entry
    cl_version, cl_body = _extract_top_changelog(repo_root)
    if cl_version != version:
        blockers.append(
            f"Top CHANGELOG entry is v{cl_version}, pyproject.toml is v{version}. Sync first."
        )
    else:
        blockers.extend(_changelog_blockers(version, cl_body))

    # 3. SECURITY.md must list the current major.minor.x line
    try:
        security_text = (repo_root / "SECURITY.md").read_text(encoding="utf-8")
        major_minor = ".".join(version.split(".")[:2])
        if f"{major_minor}.x" not in security_text:
            blockers.append(
                f"SECURITY.md does not list '{major_minor}.x' as a supported version line."
            )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Could not read SECURITY.md: {exc}")

    # 4. llms.txt must contain the matching release status line
    try:
        llms_text = (repo_root / "llms.txt").read_text(encoding="utf-8")
        if f"Release status: v{version}" not in llms_text:
            blockers.append(
                f"llms.txt does not contain 'Release status: v{version}'. Update it."
            )
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Could not read llms.txt: {exc}")

    # 5. blast_reports — must exist for current HEAD SHA when src/drift changed
    try:
        head_result = _git("rev-parse", "--short", "HEAD", cwd=repo_root)
        head_sha = head_result.stdout.strip() if head_result.returncode == 0 else ""
        drift_changed = _git(
            "diff", "--name-only", "HEAD~1", "HEAD", "--", "src/drift/", cwd=repo_root
        )
        if drift_changed.returncode == 0 and drift_changed.stdout.strip():
            blast_files = list((repo_root / "blast_reports").glob(f"*_{head_sha}.json"))
            if not blast_files:
                blockers.append(
                    f"No blast_reports/*_{head_sha}.json found for HEAD {head_sha}. "
                    "Run: DRIFT_BLAST_LIVE=1 git push (or generate manually)."
                )
        elif head_sha:
            # No src/drift changes — blast report not required
            pass
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Blast report check failed: {exc}")

    status = "GO" if not blockers else "NO_GO"
    if status == "GO":
        agent_instruction = (
            f"Release v{version} is GO. All pre-push gates are satisfied. "
            "Proceed with: git push origin master."
        )
    else:
        agent_instruction = (
            f"Release v{version} is NO_GO. Fix {len(blockers)} blocker(s) before pushing. "
            "See 'blockers' list for required actions."
        )

    return json.dumps(
        {
            "version": version,
            "status": status,
            "blockers": blockers,
            "warnings": warnings,
            "agent_instruction": agent_instruction,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Tool: drift_working_tree_context
# ---------------------------------------------------------------------------

_GATE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^src/drift/signals/"), "audit-diff (§18): signals changed → update audit_results/"),
    (re.compile(r"^src/drift/"), "blast-radius: src/drift changes → run DRIFT_BLAST_LIVE=1 git push"),
    (re.compile(r"^src/drift/"), "pre-push: model-consistency check runs automatically"),
    (re.compile(r"^src/drift/"), "pre-push: release-discipline check runs automatically"),
    (re.compile(r"^docs/|^docs-site/"), "mkdocs: docs changed → verify site/ builds cleanly"),
    (re.compile(r"^\.github/workflows/"), "CI: workflow changed → validate YAML with actionlint"),
    (re.compile(r"^pyproject\.toml$"), "pre-push: release-discipline version sync required"),
    (re.compile(r"^CHANGELOG\.md$"), "pre-push: release-discipline curated-bullets check"),
    (re.compile(r"^SECURITY\.md$"), "pre-push: model-consistency supported-version check"),
    (re.compile(r"^llms\.txt$"), "pre-push: release-discipline release-status sync check"),
]

_COMMIT_TYPE_HINTS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"^src/drift/signals/"), "feat"),
    (re.compile(r"^src/drift/"), "feat"),
    (re.compile(r"^tests/"), "test"),
    (re.compile(r"^docs/|^docs-site/|^README\.md$"), "docs"),
    (re.compile(r"^\.github/workflows/"), "ci"),
    (re.compile(r"^scripts/"), "chore"),
    (re.compile(r"^CHANGELOG\.md$|^SECURITY\.md$|^llms\.txt$"), "chore"),
    (re.compile(r"^pyproject\.toml$"), "chore"),
]


@mcp.tool()
async def drift_working_tree_context() -> str:  # type: ignore[empty-body]
    """Snapshot the current working tree and derive which pre-push gates will fire.

    Collects:
    - Files with uncommitted changes (staged + unstaged + untracked)
    - Count of changes per top-level directory
    - Inferred conventional-commit type from changed paths
    - Whether a blast_reports/ entry exists for current HEAD SHA
    - List of pre-push gates triggered by the changed paths
    - Recommended next action for the agent

    Returns JSON:
        {
            "head_sha": "...",
            "changed_files": {"src/drift/signals": 3, ...},
            "inferred_commit_type": "feat",
            "blast_report_exists_for_head": false,
            "gates_triggered": ["audit-diff ...", ...],
            "recommended_next_action": "...",
            "agent_instruction": "..."
        }
    """
    repo_root = _REPO_ROOT

    # --- HEAD SHA ---
    head_result = _git("rev-parse", "--short", "HEAD", cwd=repo_root)
    head_sha = head_result.stdout.strip() if head_result.returncode == 0 else "unknown"

    # --- Changed files (porcelain, covers staged + unstaged + untracked) ---
    status_result = _git("status", "--porcelain", cwd=repo_root)
    all_paths: list[str] = []
    if status_result.returncode == 0:
        for raw in status_result.stdout.splitlines():
            # porcelain format: "XY path" or "XY path -> dest"
            parts = raw[3:].split(" -> ")
            path = parts[-1].strip().strip('"')
            if path:
                all_paths.append(path)

    # Count by top-level group (up to 2 levels for signal detail)
    dir_counts: dict[str, int] = {}
    for p in all_paths:
        parts = p.split("/")
        key = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
        dir_counts[key] = dir_counts.get(key, 0) + 1

    # --- Infer commit type ---
    inferred = "chore"
    for pattern, ctype in _COMMIT_TYPE_HINTS:
        for p in all_paths:
            if pattern.match(p):
                inferred = ctype
                break
        # Prefer feat/fix over docs/ci/chore
        if inferred in ("feat", "fix"):
            break

    # --- Gates triggered ---
    seen_gates: set[str] = set()
    gates: list[str] = []
    for pattern, gate in _GATE_RULES:
        if gate in seen_gates:
            continue
        for p in all_paths:
            if pattern.match(p):
                seen_gates.add(gate)
                gates.append(gate)
                break

    # --- Blast report for HEAD ---
    blast_exists = bool(list((repo_root / "blast_reports").glob(f"*_{head_sha}.json")))

    # --- Recommended action ---
    if not all_paths:
        recommended = "Working tree is clean. Ready to push."
    elif any("blast-radius" in g for g in gates) and not blast_exists:
        recommended = (
            f"Blast report missing for HEAD {head_sha}. "
            "Push with: DRIFT_BLAST_LIVE=1 git push origin master"
        )
    elif gates:
        recommended = (
            f"Run 'make gate-check COMMIT_TYPE={inferred}' to verify all gates before pushing."
        )
    else:
        recommended = "No critical gates triggered. Standard 'git push origin master' should succeed."

    agent_instruction = (
        f"Working tree has {len(all_paths)} changed file(s). "
        f"Inferred commit type: {inferred}. "
        f"{len(gates)} pre-push gate(s) will fire. "
        + (f"Blast report for HEAD {head_sha} is {'present' if blast_exists else 'MISSING'}. " if gates else "")
        + f"Recommended: {recommended}"
    )

    return json.dumps(
        {
            "head_sha": head_sha,
            "changed_files": dir_counts,
            "total_changed": len(all_paths),
            "inferred_commit_type": inferred,
            "blast_report_exists_for_head": blast_exists,
            "gates_triggered": gates,
            "recommended_next_action": recommended,
            "agent_instruction": agent_instruction,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Tool: drift_audit_freshness
# ---------------------------------------------------------------------------


@mcp.tool()
async def drift_audit_freshness() -> str:  # type: ignore[empty-body]
    """Check whether §18 audit artefacts are fresh relative to last signals change.

    Per POLICY §18, whenever src/drift/signals/ changes the four audit artefacts
    (fmea_matrix.md, stride_threat_model.md, risk_register.md, fault_trees.md)
    must be updated in the same commit or the following commit.

    Heuristic: compares the last git-tracked mtime of each audit file against the
    timestamp of the most recent commit that touched src/drift/signals/.

    Returns JSON:
        {
            "signals_last_commit_sha": "...",
            "signals_last_commit_at": "ISO-8601",
            "artifacts": {
                "fmea_matrix.md": {"last_commit_sha": "...", "last_commit_at": "...", "stale": false},
                ...
            },
            "all_fresh": true,
            "stale_files": [],
            "agent_instruction": "..."
        }
    """
    repo_root = _REPO_ROOT

    def _git_last_commit(path_glob: str) -> tuple[str, str]:
        """Return (sha, iso_timestamp) of the most recent commit touching path_glob."""
        result = _git(
            "log", "--format=%H %cI", "-1", "--", path_glob, cwd=repo_root
        )
        if result.returncode != 0 or not result.stdout.strip():
            return "", ""
        parts = result.stdout.strip().split(" ", 1)
        return (parts[0], parts[1]) if len(parts) == 2 else (parts[0], "")

    def _ts(iso: str) -> datetime.datetime | None:
        if not iso:
            return None
        try:
            return datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
        except ValueError:
            return None

    # Last commit to signals
    sig_sha, sig_ts_str = _git_last_commit("src/drift/signals/")
    sig_ts = _ts(sig_ts_str)

    # Per-artifact info
    artifacts: dict[str, dict[str, object]] = {}
    stale_files: list[str] = []

    for fname in _AUDIT_FILES:
        art_sha, art_ts_str = _git_last_commit(f"audit_results/{fname}")
        art_ts = _ts(art_ts_str)

        stale = False
        if sig_ts and art_ts:
            stale = art_ts < sig_ts
        elif sig_ts and not art_ts:
            stale = True  # audit file was never committed after signals

        artifacts[fname] = {
            "last_commit_sha": art_sha or "never_committed",
            "last_commit_at": art_ts_str or "never_committed",
            "stale": stale,
        }
        if stale:
            stale_files.append(fname)

    all_fresh = len(stale_files) == 0

    if not sig_sha:
        agent_instruction = (
            "No commits found touching src/drift/signals/ — freshness check not applicable."
        )
    elif all_fresh:
        agent_instruction = (
            f"All 4 §18 audit artefacts are fresh relative to signals commit {sig_sha[:8]}. "
            "No action needed."
        )
    else:
        agent_instruction = (
            f"{len(stale_files)} audit artefact(s) are STALE relative to signals commit "
            f"{sig_sha[:8]} ({sig_ts_str}). Update: {', '.join(stale_files)}. "
            "Run: make audit-diff  — then update the stale files."
        )

    return json.dumps(
        {
            "signals_last_commit_sha": sig_sha,
            "signals_last_commit_at": sig_ts_str,
            "artifacts": artifacts,
            "all_fresh": all_fresh,
            "stale_files": stale_files,
            "agent_instruction": agent_instruction,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
