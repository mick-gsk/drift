"""Callers that still depend on legacy bridge — DO NOT remove bridge until all migrated."""

from legacy_bridge import bridge_convert, legacy_serialize


def export_report_v1(data: dict) -> str:
    """Export using v1 format for legacy downstream consumers."""
    return legacy_serialize(data)


def validate_round_trip(data: dict) -> bool:
    """Validate data survives v1 round-trip (used in migration tests)."""
    converted = bridge_convert(data)
    return set(converted.keys()) == set(data.keys())
