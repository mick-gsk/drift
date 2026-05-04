"""Pydantic models for drift retrieval (ADR-091).

All models are frozen to guarantee immutability after construction.
Corpus state flows through the system as value objects only.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Bump when chunk schema or serialisation changes incompatibly.
CORPUS_SCHEMA_VERSION = 1


class FactChunk(BaseModel):
    """A single retrievable fact with a stable identifier and source anchor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str = Field(description="Stable structured identifier (see ADR-091).")
    kind: str = Field(description="One of: policy, roadmap, adr, audit, signal, evidence.")
    source_path: str = Field(description="Posix-relative path within the repository.")
    line_start: int = Field(ge=1, description="1-based inclusive start line in the source.")
    line_end: int = Field(ge=1, description="1-based inclusive end line in the source.")
    text: str = Field(description="Verbatim chunk content.")
    sha256: str = Field(description="SHA-256 hex digest of the chunk text.")
    tags: tuple[str, ...] = Field(
        default=(), description="Structured tags (e.g. signal_id, adr_number, section)."
    )


class RetrievalResult(BaseModel):
    """A single scored hit returned by ``drift_retrieve``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fact_id: str
    kind: str
    source_path: str
    line_range: tuple[int, int]
    excerpt: str = Field(description="Text of the chunk (possibly truncated by caller).")
    sha256: str
    tags: tuple[str, ...] = ()
    score: float = Field(description="BM25 relevance score.")


class SourceEntry(BaseModel):
    """Manifest entry for a single source file contributing to the corpus."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(description="Posix-relative path within the repository.")
    mtime_ns: int = Field(description="File mtime in nanoseconds at build time.")
    sha256: str = Field(description="SHA-256 hex digest of the file contents.")
    chunk_count: int = Field(ge=0, description="Number of chunks produced from this source.")


class CorpusManifest(BaseModel):
    """Manifest describing a built corpus snapshot for staleness checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(default=CORPUS_SCHEMA_VERSION)
    corpus_sha256: str = Field(
        description="Deterministic digest over all chunk fact_ids and sha256s."
    )
    chunk_count: int = Field(ge=0)
    sources: tuple[SourceEntry, ...] = Field(default=())
    built_at: str = Field(description="ISO-8601 UTC timestamp of build.")
