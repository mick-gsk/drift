"""Compatibility shim — moved to `drift.retrieval.mcp` (ADR-099).

The real implementation now lives in the retrieval slice. This module is a
thin re-export so legacy importers (`from drift_mcp.mcp_router_retrieval import
run_retrieve` etc.) keep working. New code should import from
`drift.retrieval.mcp` directly.
"""

from drift.retrieval.mcp import *  # noqa: F401,F403
