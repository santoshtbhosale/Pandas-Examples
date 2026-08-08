from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_TEAM_LEADER = "team_leader"
ROLE_ENGINEER = "engineer"
ROLE_VIEWER = "viewer"

USER_ROLES = (
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_TEAM_LEADER,
    ROLE_ENGINEER,
    ROLE_VIEWER,
)

ROLE_LABELS: Dict[str, str] = {
    ROLE_SUPER_ADMIN: "Super Admin",
    ROLE_ADMIN: "Administrator",
    ROLE_TEAM_LEADER: "Team Leader",
    ROLE_ENGINEER: "Engineer",
    ROLE_VIEWER: "Viewer",
}

PRIVILEGED_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_ADMIN})
MANAGEMENT_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_TEAM_LEADER})


@dataclass
class UserSession:
    user_id: int
    username: str
    full_name: str
    role: str
    email: str = ""
    employee_id: str = ""
    team: str = ""
    team_leader_id: int = 0

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role.title())

    def is_super_admin(self) -> bool:
        return self.role == ROLE_SUPER_ADMIN

    def is_admin_level(self) -> bool:
        return self.role in PRIVILEGED_ROLES

    def is_team_leader(self) -> bool:
        return self.role == ROLE_TEAM_LEADER

    def is_engineer(self) -> bool:
        return self.role == ROLE_ENGINEER

    def can_manage_users(self) -> bool:
        return self.role == ROLE_SUPER_ADMIN

    def can_launch_water_demand(self) -> bool:
        return self.role in (ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_ENGINEER)

    def can_assign_projects(self) -> bool:
        return self.role in MANAGEMENT_ROLES

    def can_access_project(
        self,
        created_by: str = "",
        engineer_name: str = "",
        assigned_to_username: str = "",
        team_leader_id: int = 0,
        team_engineer_ids: Optional[List[int]] = None,
    ) -> bool:
        if self.role in PRIVILEGED_ROLES:
            return True
        if self.role == ROLE_TEAM_LEADER:
            if team_leader_id and team_leader_id == self.user_id:
                return True
            if assigned_to_username and team_engineer_ids:
                return assigned_to_username in team_engineer_ids
            return False
        if self.role == ROLE_ENGINEER:
            if assigned_to_username and assigned_to_username == self.username:
                return True
            owner = (created_by or "").strip()
            if not owner:
                return (engineer_name or "").strip().lower() == self.full_name.strip().lower()
            return owner == self.username
        if self.role == ROLE_VIEWER:
            return False
        return False

    def can_view_project_list(self) -> bool:
        return self.role != ROLE_VIEWER or True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "full_name": self.full_name,
            "role": self.role,
            "email": self.email,
            "employee_id": self.employee_id,
            "team": self.team,
            "team_leader_id": self.team_leader_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSession":
        return cls(
            user_id=int(data.get("user_id", 0)),
            username=str(data.get("username", "")),
            full_name=str(data.get("full_name", "")),
            role=str(data.get("role", ROLE_VIEWER)),
            email=str(data.get("email", "")),
            employee_id=str(data.get("employee_id", "")),
            team=str(data.get("team", "")),
            team_leader_id=int(data.get("team_leader_id", 0) or 0),
        )


@dataclass
class UserRecord(UserSession):
    is_active: bool = True
    created_at: str = ""
