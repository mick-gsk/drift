"""Change-Detector: ermittelt geänderte Dateien aus Git-Diff oder Worktree.

Nutzt stdlib + ``subprocess`` direkt (keine GitPython-Dependency), analog zu
anderen Drift-Komponenten. Pfade werden immer als POSIX-relative Strings
zurückgegeben, damit Glob-Matcher stabil arbeiten.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger("drift.blast_radius")


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """Ergebnis einer Change-Detection."""

    changed_files: tuple[str, ...]
    head_sha: str | None
    ref: str
    head: str


def _run_git(args: list[str], cwd: Path) -> tuple[int, str]:
    """Führe Git deterministisch aus und liefere (returncode, stdout_str)."""
    try:
        completed = subprocess.run(  # noqa: S603 — controlled args
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        _log.debug("git %s failed: %s", args, exc)
        return 1, ""
    return completed.returncode, completed.stdout


def _normalize(paths: list[str]) -> tuple[str, ...]:
    """POSIX-Normalisierung + Deduplikation + stabile Sortierung."""
    seen: set[str] = set()
    result: list[str] = []
    for p in paths:
        if not p:
            continue
        normalized = p.replace("\\", "/").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    result.sort()
    return tuple(result)


def detect_changes(
    repo_path: Path,
    *,
    ref: str = "HEAD",
    head: str = "HEAD",
    explicit_changed_files: list[str] | None = None,
) -> ChangeSet:
    """Ermittle die Menge geänderter Dateien.

    Reihenfolge:

    1. Wenn ``explicit_changed_files`` gesetzt ist, wird diese Liste benutzt
       (kein Git-Call, für Test-Determinismus und Agent-Override).
    2. Sonst ``git diff --name-only <ref>..<head>`` plus Working-Tree-Diff
       gegen ``head`` (staged + unstaged), vereinigt.
    3. Wenn kein Git-Repo → leere Changeset.
    """
    if explicit_changed_files is not None:
        rc, head_sha = _run_git(["rev-parse", head], repo_path)
        resolved_sha = head_sha.strip() if rc == 0 and head_sha.strip() else None
        return ChangeSet(
            changed_files=_normalize(explicit_changed_files),
            head_sha=resolved_sha,
            ref=ref,
            head=head,
        )

    if not (repo_path / ".git").exists():
        _log.debug("No .git directory at %s — empty changeset", repo_path)
        return ChangeSet(changed_files=(), head_sha=None, ref=ref, head=head)

    collected: list[str] = []

    # Range-Diff
    rc, out = _run_git(["diff", "--name-only", f"{ref}..{head}"], repo_path)
    if rc == 0 and out.strip():
        collected.extend(out.splitlines())

    # Staged + unstaged vs. HEAD, damit aktuelle Edits einbezogen werden
    if head == "HEAD":
        rc2, out2 = _run_git(["diff", "--name-only", "HEAD"], repo_path)
        if rc2 == 0 and out2.strip():
            collected.extend(out2.splitlines())
        rc3, out3 = _run_git(["diff", "--name-only", "--cached"], repo_path)
        if rc3 == 0 and out3.strip():
            collected.extend(out3.splitlines())

    rc_sha, sha = _run_git(["rev-parse", head], repo_path)
    resolved_head_sha: str | None = (
        sha.strip() if rc_sha == 0 and sha.strip() else None
    )

    return ChangeSet(
        changed_files=_normalize(collected),
        head_sha=resolved_head_sha,
        ref=ref,
        head=head,
    )


def short_sha(sha: str | None) -> str:
    """Kürze einen Commit-SHA auf 7 Zeichen; fallback ``nohead``."""
    if not sha:
        return "nohead"
    return sha[:7]


def resolve_repo_path(path: str | os.PathLike[str]) -> Path:
    """Normalisiere und validiere den Repo-Pfad.

    Raises ``ValueError``, wenn der Pfad nicht existiert.
    """
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_dir():
        msg = f"Repository-Pfad existiert nicht oder ist kein Verzeichnis: {path}"
        raise ValueError(msg)
    return resolved
