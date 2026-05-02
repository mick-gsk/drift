"""Resolve one-hop TypeScript barrel re-exports from index.ts files."""

from __future__ import annotations

import posixpath
import re
from dataclasses import dataclass
from pathlib import Path

_EXPORT_STAR_RE = re.compile(
    r"^\s*export\s+\*\s+from\s+[\"']([^\"']+)[\"']\s*;?\s*$"
)
_EXPORT_NAMED_RE = re.compile(
    r"^\s*export\s*\{([^}]*)\}\s*from\s+[\"']([^\"']+)[\"']\s*;?\s*$"
)


@dataclass(frozen=True)
class BarrelExport:
    """Represents a single barrel re-export statement."""

    module_spec: str
    exported_names: set[str] | None


def _normalize_rel_path(path: Path) -> Path:
    """Normalize a repository-relative path using POSIX semantics."""
    return Path(posixpath.normpath(path.as_posix()))


def _resolve_relative_target(repo_path: Path, source_path: Path, module_spec: str) -> Path | None:
    """Resolve relative TS module specifier to repository-relative target file."""
    if not (module_spec.startswith("./") or module_spec.startswith("../")):
        return None

    base_candidate = _normalize_rel_path(source_path.parent / module_spec)

    if base_candidate.suffix in {".ts", ".tsx"}:
        explicit = repo_path / base_candidate
        return base_candidate if explicit.is_file() else None

    for suffix in (".ts", ".tsx"):
        candidate = _normalize_rel_path(Path(f"{base_candidate.as_posix()}{suffix}"))
        if (repo_path / candidate).is_file():
            return candidate

    for index_name in ("index.ts", "index.tsx"):
        index_candidate = _normalize_rel_path(base_candidate / index_name)
        if (repo_path / index_candidate).is_file():
            return index_candidate

    return None


def _parse_named_export_names(export_clause: str) -> set[str]:
    """Parse exported names from ``export { ... } from`` clause."""
    names: set[str] = set()
    for part in export_clause.split(","):
        token = part.strip()
        if not token:
            continue

        if token.startswith("type "):
            token = token[len("type ") :].strip()

        if " as " in token:
            _, exported_name = token.split(" as ", 1)
            exported_name = exported_name.strip()
            if exported_name:
                names.add(exported_name)
            continue

        names.add(token)

    return names


def _extract_barrel_exports(index_text: str) -> list[BarrelExport]:
    """Extract one-hop re-exports from an index.ts source file."""
    exports: list[BarrelExport] = []

    for line in index_text.splitlines():
        star_match = _EXPORT_STAR_RE.match(line)
        if star_match:
            exports.append(BarrelExport(module_spec=star_match.group(1), exported_names=None))
            continue

        named_match = _EXPORT_NAMED_RE.match(line)
        if named_match:
            exports.append(
                BarrelExport(
                    module_spec=named_match.group(2),
                    exported_names=_parse_named_export_names(named_match.group(1)),
                )
            )

    return exports


def resolve_index_barrel_target(
    repo_path: Path,
    index_path: Path,
    imported_symbols: set[str] | None,
) -> Path | None:
    """Resolve imports targeting index.ts to a one-hop re-export source file.

    Returns a repository-relative target file only when a single unambiguous
    re-export target can be selected.
    """
    if index_path.name not in {"index.ts", "index.tsx"}:
        return None

    index_text = (repo_path / index_path).read_text(encoding="utf-8", errors="replace")
    candidates: set[Path] = set()

    for barrel_export in _extract_barrel_exports(index_text):
        if barrel_export.exported_names is not None:
            if imported_symbols is None:
                continue
            if not (barrel_export.exported_names & imported_symbols):
                continue

        resolved = _resolve_relative_target(repo_path, index_path, barrel_export.module_spec)
        if resolved is None:
            continue
        candidates.add(resolved)

    if len(candidates) != 1:
        return None

    return next(iter(candidates))
