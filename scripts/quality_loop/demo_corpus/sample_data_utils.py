"""Sample data utilities — quality loop demo corpus.

This file intentionally contains ruff-detectable violations (F401 unused
imports) so that the RemoveUnusedImports transform can demonstrate measurable
improvement on a known corpus.
"""

import os
import sys        # unused  (F401)
import json
import re         # unused  (F401)
import hashlib    # unused  (F401)
import logging    # unused  (F401)
from typing import Optional


def load_json(path: str) -> Optional[dict]:
    """Load JSON from path."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def join_paths(base: str, *parts: str) -> str:
    """Join path components."""
    return os.path.join(base, *parts)


def format_value(value: object) -> str:
    """Format a value for display."""
    return str(value)
