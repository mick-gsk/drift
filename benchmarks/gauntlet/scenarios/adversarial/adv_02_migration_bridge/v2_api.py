"""v2 API — new callers should use this module directly."""


def v2_serialize(data: dict) -> str:
    """Serialize using the v2 JSON format."""
    import json
    return json.dumps(data, sort_keys=True)


def v2_deserialize(raw: str) -> dict:
    """Deserialize v2 JSON format."""
    import json
    return json.loads(raw)
