"""Pre-/Post-Merge Re-Score ueber ``git worktree`` (ADR-088).

Liefert zwei :class:`drift.models.RepoAnalysis`-Snapshots fuer ein
Commit-Paar.  Das primaere Arbeitsverzeichnis des Users wird dabei **nie**
angefasst - die Analyse laeuft jeweils in einem detached worktree, der
garantiert aufgeraeumt wird.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from drift.analyzer import analyze_repo
from drift.config import DriftConfig
from drift.models import RepoAnalysis


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


@contextmanager
def _detached_worktree(repo_path: Path, commit_sha: str) -> Iterator[Path]:
    """Temporary detached worktree at ``commit_sha``.

    Cleanup via ``git worktree remove --force`` ist durch ``finally``
    abgesichert; falls git selbst scheitert (z. B. weil der Pfad bereits
    geloescht ist), faellt die Implementierung auf ``shutil.rmtree`` zurueck.
    """

    tmp_root = Path(tempfile.mkdtemp(prefix="drift-outcome-"))
    wt_path = tmp_root / "worktree"
    try:
        _run_git(repo_path, "worktree", "add", "--detach", str(wt_path), commit_sha)
        try:
            yield wt_path
        finally:
            with suppress(subprocess.CalledProcessError):
                _run_git(repo_path, "worktree", "remove", "--force", str(wt_path))
    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root, ignore_errors=True)


def analyze_commit_pair(
    repo_path: Path,
    parent_sha: str,
    merge_sha: str,
    config: DriftConfig | None = None,
) -> tuple[RepoAnalysis, RepoAnalysis]:
    """Analysiere ``parent_sha`` und ``merge_sha`` in isolierten Worktrees.

    Returns ``(pre, post)`` in dieser Reihenfolge.  Der Haupt-Worktree
    des Repos bleibt unberuehrt - weder HEAD noch die Working Tree Dateien
    aendern sich.
    """

    repo_path = repo_path.resolve()

    with _detached_worktree(repo_path, parent_sha) as wt_parent:
        pre = analyze_repo(wt_parent, config=config)

    with _detached_worktree(repo_path, merge_sha) as wt_merge:
        post = analyze_repo(wt_merge, config=config)

    return pre, post


__all__ = ["analyze_commit_pair"]
