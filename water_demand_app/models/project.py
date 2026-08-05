from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict


@dataclass
class RevisionInfo:
    date: str = ""
    revision_no: str = "R0"
    description: str = "ISSUED FOR REFERENCE"
    prepared_by: str = ""
    checked_by: str = ""
    approved_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RevisionInfo":
        return cls(**{k: data.get(k, getattr(cls, k, "")) for k in cls.__dataclass_fields__})


@dataclass
class ProjectData:
    project_id: str = ""
    project_name: str = "PROPOSED RESIDENTIAL"
    client_name: str = "MR. ABC"
    project_location: str = "PUNE"
    engineer_name: str = "AKASH KHADE"
    project_no: str = ""
    date: str = ""
    revision: RevisionInfo = field(default_factory=RevisionInfo)

    def __post_init__(self) -> None:
        if not self.project_id:
            self.project_id = "WD-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not self.date:
            self.date = datetime.now().strftime("%d-%m-%Y")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "project_location": self.project_location,
            "engineer_name": self.engineer_name,
            "project_no": self.project_no,
            "date": self.date,
            "revision": self.revision.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectData":
        revision_data = data.get("revision", {})
        if isinstance(revision_data, dict):
            revision = RevisionInfo.from_dict(revision_data)
        else:
            revision = RevisionInfo()
        return cls(
            project_id=data.get("project_id", ""),
            project_name=data.get("project_name", data.get("Project Name", "PROPOSED RESIDENTIAL")),
            client_name=data.get("client_name", data.get("Client Name", "MR. ABC")),
            project_location=data.get("project_location", data.get("Project Location", "PUNE")),
            engineer_name=data.get("engineer_name", data.get("Engineer Name", "AKASH KHADE")),
            project_no=data.get("project_no", data.get("Project No.", "")),
            date=data.get("date", data.get("Date", "")),
            revision=revision,
        )

    def legacy_dict(self) -> Dict[str, str]:
        return {
            "Project Name": self.project_name,
            "Client Name": self.client_name,
            "Project Location": self.project_location,
            "Engineer Name": self.engineer_name,
            "Project No.": self.project_no,
            "Date": self.date,
        }
