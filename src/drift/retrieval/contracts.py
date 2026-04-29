"""Public contracts for the ``drift.retrieval`` slice (ADR-099).

This module is intentionally minimal. ``contracts.py`` declares the slice's
public surface, but for the retrieval slice the contract is identical to the
existing public re-exports in ``drift.retrieval.__init__`` and the data models
in ``drift.retrieval.models``. Importing from this module is equivalent to
importing from those locations and is the recommended path for code that
wants to express an explicit dependency on the retrieval slice contract.

ADR-099: Vertical-Slice-Architektur — every slice MUST expose a ``contracts.py``
module so that consumers can import the slice's public API from a single,
stable location even if internal modules are reorganised.
"""

from drift.retrieval.models import (
    CorpusManifest,
    FactChunk,
    RetrievalResult,
    SourceEntry,
)

__all__ = [
    "CorpusManifest",
    "FactChunk",
    "RetrievalResult",
    "SourceEntry",
]
