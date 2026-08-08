"""Project assignment, timer, and status workflow metadata."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_PAUSED = "paused"
STATUS_COMPLETED = "completed"
STATUS_DELAYED = "delayed"
STATUS_PENDING_APPROVAL = "pending_approval"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

OUTCOME_EARLY = "completed_early"
OUTCOME_ON_TIME = "completed_on_time"
OUTCOME_LATE = "completed_late"

DURATION_PRESETS_MINUTES = {
    "30 Minutes": 30,
    "1 Hour": 60,
    "2 Hours": 120,
    "4 Hours": 240,
    "8 Hours": 480,
}


@dataclass
class ProjectWorkflow:
    assigned_to_username: str = ""
    assigned_by_username: str = ""
    team_leader_id: int = 0
    assigned_at: str = ""
    expected_completion_at: str = ""
    project_opened_at: str = ""
    completed_at: str = ""
    paused_at: str = ""
    total_paused_seconds: int = 0
    priority: str = "Normal"
    status: str = STATUS_NOT_STARTED
    progress_pct: int = 0
    delay_seconds: int = 0
    total_time_taken_seconds: int = 0
    completion_outcome: str = ""
    assigned_duration_minutes: int = 0
    project_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectWorkflow":
        if not data:
            return cls()
        fields = {k: data.get(k, getattr(cls(), k)) for k in cls.__dataclass_fields__}
        return cls(**fields)
