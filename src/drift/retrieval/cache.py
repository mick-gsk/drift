"""Corpus cache with mtime+sha256 staleness check (ADR-091).

The first :func:`load_or_build` call per MCP session hits disk; subsequent
calls reuse the in-memory result. The on-disk manifest is deterministic
and guards against silent staleness when fact sources change.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from drift.retrieval.corpus_builder import build_corpus, compute_corpus_sha256
from drift.retrieval.models import (
    CORPUS_SCHEMA_VERSION,
    CorpusManifest,
    FactChunk,
    SourceEntry,
)

logger = logging.getLogger("drift.retrieval.cache")

_MANIFEST_FILENAME = "corpus_manifest.json"
_CHUNKS_FILENAME = "corpus_chunks.json"
_CACHE_SUBDIR = Path(".drift-cache") / "retrieval"

_DEFAULT_TRACKED_SOURCES: tuple[str, ...] = (
    "POLICY.md",
    "ROADMAP.md",
)
_DEFAULT_TRACKED_DIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decisions", ("ADR-*.md",)),
    ("audit_results", ("*.md",)),
    ("src/drift/signals", ("*.py",)),
    ("benchmark_results", ("v*_feature_evidence.json",)),
)

# Per-repo-root in-memory cache, guarded by ``_lock``. Keeps the corpus alive
# for the lifetime of a process (e.g. an MCP server session).
_lock = threading.Lock()
_in_memory: dict[Path, tuple[CorpusManifest, list[FactChunk]]] = {}


def _tracked_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for name in _DEFAULT_TRACKED_SOURCES:
        p = repo_root / name
        if p.exists():
            files.append(p)
    for dir_name, patterns in _DEFAULT_TRACKED_DIRS:
        base = repo_root / dir_name
        if not base.exists():
            continue
        for pattern in patterns:
            files.extend(sorted(base.glob(pattern)))
    return sorted({f.resolve() for f in files})


def _source_entry(path: Path, repo_root: Path, chunk_count: int) -> SourceEntry:
    data = path.read_bytes()
    return SourceEntry(
        path=path.resolve().relative_to(repo_root).as_posix(),
        mtime_ns=path.stat().st_mtime_ns,
        sha256=hashlib.sha256(data).hexdigest(),
        chunk_count=chunk_count,
    )


def _build_manifest(
    repo_root: Path, chunks: list[FactChunk]
) -> CorpusManifest:
    per_source: dict[str, int] = {}
    for chunk in chunks:
        per_source[chunk.source_path] = per_source.get(chunk.source_path, 0) + 1
    sources: list[SourceEntry] = []
    for path in _tracked_files(repo_root):
        rel = path.resolve().relative_to(repo_root).as_posix()
        sources.append(_source_entry(path, repo_root, per_source.get(rel, 0)))
    manifest = CorpusManifest(
        schema_version=CORPUS_SCHEMA_VERSION,
        corpus_sha256=compute_corpus_sha256(chunks),
        chunk_count=len(chunks),
        sources=tuple(sources),
        built_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    return manifest


def _cache_dir(repo_root: Path, override: Path | None) -> Path:
    if override is not None:
        return override
    return repo_root / _CACHE_SUBDIR


def _write_cache(cache_dir: Path, manifest: CorpusManifest, chunks: list[FactChunk]) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / _MANIFEST_FILENAME).write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )
    (cache_dir / _CHUNKS_FILENAME).write_text(
        json.dumps([c.model_dump() for c in chunks], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_cache(cache_dir: Path) -> tuple[CorpusManifest, list[FactChunk]] | None:
    manifest_path = cache_dir / _MANIFEST_FILENAME
    chunks_path = cache_dir / _CHUNKS_FILENAME
    if not manifest_path.exists() or not chunks_path.exists():
        return None
    try:
        manifest = CorpusManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if manifest.schema_version != CORPUS_SCHEMA_VERSION:
        return None
    try:
        raw = json.loads(chunks_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(raw, list):
        return None
    try:
        chunks = [FactChunk.model_validate(record) for record in raw]
    except ValueError:
        return None
    return manifest, chunks


def _manifest_matches_disk(manifest: CorpusManifest, repo_root: Path) -> bool:
    recorded = {entry.path: entry for entry in manifest.sources}
    actual_files = _tracked_files(repo_root)
    actual_paths = {
        f.resolve().relative_to(repo_root).as_posix(): f for f in actual_files
    }
    if set(recorded.keys()) != set(actual_paths.keys()):
        return False
    for rel, path in actual_paths.items():
        entry = recorded[rel]
        if path.stat().st_mtime_ns == entry.mtime_ns:
            continue
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != entry.sha256:
            return False
    return True


def load_or_build(
    repo_root: Path,
    *,
    cache_dir: Path | None = None,
    force_rebuild: bool = False,
) -> tuple[CorpusManifest, list[FactChunk]]:
    """Return the current corpus, rebuilding only when sources have changed.

    Layers of caching:

    1. In-memory cache keyed by resolved repo root (process-lifetime).
    2. On-disk manifest + chunks under ``.drift-cache/retrieval/``.
    3. Full rebuild when the manifest is missing, outdated, or stale.
    """
    repo_root = repo_root.resolve()
    cache_path = _cache_dir(repo_root, cache_dir)

    with _lock:
        cached = _in_memory.get(repo_root)
        if cached and not force_rebuild and _manifest_matches_disk(cached[0], repo_root):
            return cached

        if not force_rebuild:
            disk = _read_cache(cache_path)
            if disk and _manifest_matches_disk(disk[0], repo_root):
                _in_memory[repo_root] = disk
                return disk

        chunks = build_corpus(repo_root)
        manifest = _build_manifest(repo_root, chunks)
        try:
            _write_cache(cache_path, manifest, chunks)
        except OSError as exc:  # cache is best-effort; never fail retrieval because of it
            logger.warning("retrieval: could not write corpus cache at %s: %s", cache_path, exc)
        result = (manifest, chunks)
        _in_memory[repo_root] = result
        return result


def clear_memory_cache() -> None:
    """Drop the process-local in-memory cache (used in tests)."""
    with _lock:
        _in_memory.clear()


def iter_tracked_files(repo_root: Path) -> Iterable[Path]:
    """Expose the tracked-file list for diagnostics and testing."""
    yield from _tracked_files(repo_root.resolve())
