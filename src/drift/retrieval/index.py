"""Deterministic BM25 index for drift retrieval (ADR-091).

A minimal Okapi-BM25 implementation so the retrieval layer has zero new
hard dependencies. Scores and ordering are fully deterministic: ties
break on ``fact_id`` lexicographically, never on insertion order.

Parameters follow the common defaults (``k1 = 1.5``, ``b = 0.75``)
documented in Robertson & Zaragoza, *The Probabilistic Relevance
Framework: BM25 and Beyond* (FnT IR 3:4, 2009).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from drift.retrieval.models import FactChunk

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_DEFAULT_K1 = 1.5
_DEFAULT_B = 0.75


def tokenize(text: str) -> list[str]:
    """Split text into lowercased alphanumeric tokens."""
    return [m.group(0).lower() for m in _TOKEN_RE.finditer(text)]


def _expand_chunk_terms(chunk: FactChunk) -> list[str]:
    """Build the bag-of-tokens that represents a chunk for BM25 scoring."""
    tokens = tokenize(chunk.text)
    tokens.extend(tokenize(chunk.fact_id))
    tokens.extend(tokenize(chunk.source_path))
    for tag in chunk.tags:
        tokens.extend(tokenize(tag))
    return tokens


@dataclass(frozen=True)
class _Posting:
    index: int  # position in the chunks list
    tf: int  # raw term frequency in this chunk


class BM25Index:
    """In-memory BM25 index over a list of :class:`FactChunk` records.

    The index is immutable after construction. Callers rebuild the index
    whenever the underlying corpus changes (tracked via the corpus
    manifest, see :mod:`drift.retrieval.cache`).
    """

    def __init__(
        self,
        chunks: list[FactChunk],
        *,
        k1: float = _DEFAULT_K1,
        b: float = _DEFAULT_B,
    ) -> None:
        self._chunks: tuple[FactChunk, ...] = tuple(chunks)
        self._k1 = k1
        self._b = b
        self._doc_len: list[int] = []
        self._postings: dict[str, list[_Posting]] = {}

        total_len = 0
        for i, chunk in enumerate(self._chunks):
            tokens = _expand_chunk_terms(chunk)
            total_len += len(tokens)
            self._doc_len.append(len(tokens))
            for term, tf in Counter(tokens).items():
                self._postings.setdefault(term, []).append(_Posting(i, tf))

        self._n_docs = len(self._chunks)
        self._avg_doc_len = (total_len / self._n_docs) if self._n_docs else 0.0

        # Precompute IDF per term for deterministic scoring.
        self._idf: dict[str, float] = {}
        for term, postings in self._postings.items():
            df = len(postings)
            # Robertson-Sparck-Jones IDF with the common (N - df + 0.5)/(df + 0.5) + 1.
            self._idf[term] = math.log(1.0 + (self._n_docs - df + 0.5) / (df + 0.5))

    @property
    def size(self) -> int:
        return self._n_docs

    def score(self, query_tokens: list[str], index: int) -> float:
        """Compute the BM25 score of a single document for a tokenised query."""
        if self._n_docs == 0:
            return 0.0
        doc_len = self._doc_len[index]
        denom_norm = self._k1 * (
            1.0 - self._b + self._b * (doc_len / self._avg_doc_len if self._avg_doc_len else 1.0)
        )
        score = 0.0
        for term in query_tokens:
            postings = self._postings.get(term)
            if not postings:
                continue
            tf = 0
            for posting in postings:
                if posting.index == index:
                    tf = posting.tf
                    break
            if tf == 0:
                continue
            idf = self._idf.get(term, 0.0)
            score += idf * ((tf * (self._k1 + 1.0)) / (tf + denom_norm))
        return score

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        allowed_indices: frozenset[int] | None = None,
    ) -> list[tuple[int, float]]:
        """Return the top-``top_k`` ``(chunk_index, score)`` pairs for ``query``.

        Ties in score are broken by ``fact_id`` (lexicographic ascending).
        """
        if self._n_docs == 0 or not query.strip():
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        # Collect candidate docs that share at least one query term.
        candidates: set[int] = set()
        for term in query_tokens:
            for posting in self._postings.get(term, ()):
                candidates.add(posting.index)
        if allowed_indices is not None:
            candidates &= allowed_indices
        if not candidates:
            return []

        scored = [(idx, self.score(query_tokens, idx)) for idx in candidates]
        scored = [(idx, s) for idx, s in scored if s > 0.0]
        # Deterministic tie-break: score desc, then fact_id asc.
        scored.sort(key=lambda pair: (-pair[1], self._chunks[pair[0]].fact_id))
        return scored[:top_k]

    def chunk_at(self, index: int) -> FactChunk:
        return self._chunks[index]
