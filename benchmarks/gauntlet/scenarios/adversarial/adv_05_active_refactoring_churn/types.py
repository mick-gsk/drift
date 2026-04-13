"""Type aliases being consolidated with schema.py in sprint 12.

Changes to this file are always paired with schema.py changes.
This is intentional during the migration and should NOT be stabilized prematurely.
"""

from typing import TypeAlias

UserDict: TypeAlias = dict[str, str]
ProjectDict: TypeAlias = dict[str, str]


def user_to_typed(raw: dict) -> UserDict:
    return {"name": raw["name"], "email": raw["email"], "role": raw.get("role", "viewer")}


def project_to_typed(raw: dict) -> ProjectDict:
    return {"title": raw["title"], "owner": raw["owner"], "status": raw.get("status", "active")}


def validate_user_dict(data: UserDict) -> bool:
    return "name" in data and "email" in data


def validate_project_dict(data: ProjectDict) -> bool:
    return "title" in data and "owner" in data
