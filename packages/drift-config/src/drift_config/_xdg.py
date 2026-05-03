"""XDG Base Directory Specification helpers for Drift.

Drift follows the XDG Base Directory Specification (freedesktop.org/wiki/Software/xdg-basedir)
to keep project directories clean.  On Windows the equivalent is %LOCALAPPDATA%.

Cache directory hierarchy
-------------------------
Per-project cache (parse results, signal cache, embeddings, git-history index):

    Linux/macOS : $XDG_CACHE_HOME/drift/<repo-id>/   (default ~/.cache/drift/<id>/)
    Windows     : %LOCALAPPDATA%\\drift\\<repo-id>\\

State directory (important runtime state, not user config):

    Linux/macOS : $XDG_STATE_HOME/drift/<repo-id>/   (default ~/.local/state/drift/<id>/)
    Windows     : %LOCALAPPDATA%\\drift\\state\\<repo-id>\\

Backward compatibility
----------------------
If a project already has a ``<repo>/.drift-cache/`` directory, that path is used
as-is so existing installations are not disrupted.  The directory is only migrated
to XDG when the user deletes ``<repo>/.drift-cache/`` or sets ``cache_dir`` to an
explicit value in ``drift.yaml``.

Explicit ``cache_dir`` in ``drift.yaml`` always wins.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform-aware XDG base directories
# ---------------------------------------------------------------------------


def xdg_cache_home() -> Path:
    """Return the XDG cache base directory for the current platform.

    * **Linux / macOS**: ``$XDG_CACHE_HOME`` if set; otherwise ``~/.cache``
    * **Windows**: ``%LOCALAPPDATA%`` if set; otherwise ``~/AppData/Local``
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data)
        return Path.home() / "AppData" / "Local"

    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".cache"


def xdg_state_home() -> Path:
    """Return the XDG state base directory for the current platform.

    * **Linux / macOS**: ``$XDG_STATE_HOME`` if set; otherwise ``~/.local/state``
    * **Windows**: ``%LOCALAPPDATA%\\state`` (no XDG equivalent; collocated with cache base)
    """
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "state"

    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".local" / "state"


# ---------------------------------------------------------------------------
# Repo-scoped cache paths
# ---------------------------------------------------------------------------


def _repo_id(repo_path: Path) -> str:
    """Return a short, stable identifier for a repo path.

    Uses the first 12 hex characters of SHA-1(resolved absolute path)
    to keep directory names compact and collision-resistant.
    """
    canonical = str(repo_path.resolve())
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:12]  # noqa: S324


def resolve_cache_dir(repo_path: Path, configured: str) -> Path:
    """Resolve the effective cache directory for a drift analysis run.

    Priority (highest to lowest):

    1. **Explicit config**: if ``configured`` is non-empty, return
       ``repo_path / configured`` (supports both relative and absolute values).
    2. **Legacy directory**: if ``<repo>/.drift-cache/`` already exists, keep
       using it to avoid disrupting installed setups.
    3. **XDG default**: ``$XDG_CACHE_HOME/drift/<repo-id>/``.

    Parameters
    ----------
    repo_path:
        Absolute path to the repository root.
    configured:
        The ``cache_dir`` field from ``DriftConfig``.  An empty string means
        "use the XDG default".
    """
    if configured:
        candidate = Path(configured)
        if candidate.is_absolute():
            return candidate
        return (repo_path / configured).resolve()

    # Backward-compat: keep using the legacy directory if it already exists.
    legacy = repo_path / ".drift-cache"
    if legacy.exists():
        return legacy

    # XDG default: namespaced by repo identity.
    return xdg_cache_home() / "drift" / _repo_id(repo_path)


def resolve_state_dir(repo_path: Path, configured: str = "") -> Path:
    """Resolve the effective state directory for a drift analysis run.

    State holds important runtime data (calibration status, self-improvement
    ledger) that should survive cache eviction.

    Priority mirrors :func:`resolve_cache_dir`.
    """
    if configured:
        candidate = Path(configured)
        if candidate.is_absolute():
            return candidate
        return (repo_path / configured).resolve()

    legacy = repo_path / ".drift"
    if legacy.exists():
        return legacy

    return xdg_state_home() / "drift" / _repo_id(repo_path)
