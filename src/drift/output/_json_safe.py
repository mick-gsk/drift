"""Helpers to normalize arbitrary values into deterministic JSON-safe data."""

from __future__ import annotations

import datetime
from collections.abc import Mapping, Sequence
from enum import Enum
from pathlib import Path
from typing import Any


def to_json_safe(value: Any) -> Any:
    """Recursively normalize values to JSON-native, deterministic shapes."""
    if value is None or isinstance(value, bool | int | float | str):
        return value

    if isinstance(value, Path):
        return value.as_posix()

    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()

    if isinstance(value, Enum):
        return to_json_safe(value.value)

    if isinstance(value, Mapping):
        return {str(k): to_json_safe(v) for k, v in value.items()}

    if isinstance(value, set | frozenset):
        normalized = [to_json_safe(v) for v in value]
        return sorted(normalized, key=lambda v: repr(v))

    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [to_json_safe(v) for v in value]

    return str(value)
