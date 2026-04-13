"""Active refactoring: schema module being decomposed. High churn is expected.

This file and types.py are being refactored together in sprint 12.
Co-change coupling is intentional and temporary.
See: REFACTORING.md#sprint-12-schema-decomposition
"""

from dataclasses import dataclass


@dataclass
class UserSchema:
    name: str
    email: str
    role: str = "viewer"

    def to_dict(self) -> dict:
        return {"name": self.name, "email": self.email, "role": self.role}

    @classmethod
    def from_dict(cls, data: dict) -> "UserSchema":
        return cls(name=data["name"], email=data["email"], role=data.get("role", "viewer"))


@dataclass
class ProjectSchema:
    title: str
    owner: str
    status: str = "active"

    def to_dict(self) -> dict:
        return {"title": self.title, "owner": self.owner, "status": self.status}
