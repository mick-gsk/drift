"""Migration bridge module — actively used, removal would break 50% of callers.

This module is marked deprecated in public docs but serves as the compatibility
layer for the v1→v2 API migration. It will be removed ONLY after all callers
have been migrated (tracked in MIGRATION.md).
"""
import warnings


def legacy_serialize(data: dict) -> str:
    """Serialize using the v1 format. Still required by legacy callers."""
    warnings.warn(
        "legacy_serialize is deprecated, use v2_serialize",
        DeprecationWarning,
        stacklevel=2,
    )
    parts = []
    for key, value in sorted(data.items()):
        parts.append(f"{key}={value}")
    return "&".join(parts)


def legacy_deserialize(raw: str) -> dict:
    """Deserialize v1 format strings."""
    warnings.warn(
        "legacy_deserialize is deprecated, use v2_deserialize",
        DeprecationWarning,
        stacklevel=2,
    )
    result = {}
    for pair in raw.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            result[key] = value
    return result


def bridge_convert(data: dict) -> dict:
    """Convert v1 data through serialization round-trip for compatibility testing."""
    raw = legacy_serialize(data)
    return legacy_deserialize(raw)
