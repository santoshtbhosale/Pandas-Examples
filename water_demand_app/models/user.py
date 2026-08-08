from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

ROLE_ADMIN = "admin"
ROLE_ENGINEER = "engineer"
ROLE_VIEWER = "viewer"

USER_ROLES = (ROLE_ADMIN, ROLE_ENGINEER, ROLE_VIEWER)

ROLE_LABELS: Dict[str, str] = {
    ROLE_ADMIN: "Administrator",
    ROLE_ENGINEER: "Engineer",
    ROLE_VIEWER: "Viewer",
}


@dataclass
class UserSession:
    user_id: int
    username: str
    full_name: str
    role: str
    email: str = ""

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role.title())

    def can_launch_water_demand(self) -> bool:
        return self.role in (ROLE_ADMIN, ROLE_ENGINEER)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        return cls(
            user_id=int(data.get("user_id", 0)),
            username=str(data.get("username", "")),
            full_name=str(data.get("full_name", "")),
            role=str(data.get("role", ROLE_VIEWER)),
            email=str(data.get("email", "")),
        )
