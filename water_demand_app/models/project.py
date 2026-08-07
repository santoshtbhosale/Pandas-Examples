from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict

from config.nbc_2026 import PLOT_MODE_DUAL, PROJECT_TYPE_MIXED, parse_building_config


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
    engineer_name: str = "Akash"
    project_no: str = ""
    date: str = ""
    plot_mode: str = PLOT_MODE_DUAL
    project_type: str = PROJECT_TYPE_MIXED
    building_config: str = "G+7"
    building_height_m: float = 0.0
    num_wings: int = 1
    building_type: str = "Residential Apartment"
    client_address: str = ""
    client_contact: str = ""
    client_email: str = ""
    client_gst: str = ""
    city: str = ""
    state: str = ""
    rainfall_zone: str = ""
    climate: str = ""
    revision: RevisionInfo = field(default_factory=RevisionInfo)

    def __post_init__(self) -> None:
        if not self.project_id:
            self.project_id = "WD-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        if not self.date:
            self.date = datetime.now().strftime("%d-%m-%Y")
        if self.building_height_m <= 0 and self.building_config:
            _, est_height = parse_building_config(self.building_config)
            if est_height > 0:
                self.building_height_m = est_height

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "client_name": self.client_name,
            "project_location": self.project_location,
            "engineer_name": self.engineer_name,
            "project_no": self.project_no,
            "date": self.date,
            "plot_mode": self.plot_mode,
            "project_type": self.project_type,
            "building_config": self.building_config,
            "building_height_m": self.building_height_m,
            "num_wings": self.num_wings,
            "building_type": self.building_type,
            "client_address": self.client_address,
            "client_contact": self.client_contact,
            "client_email": self.client_email,
            "client_gst": self.client_gst,
            "city": self.city,
            "state": self.state,
            "rainfall_zone": self.rainfall_zone,
            "climate": self.climate,
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
            engineer_name=data.get("engineer_name", data.get("Engineer Name", "Akash")),
            project_no=data.get("project_no", data.get("Project No.", "")),
            date=data.get("date", data.get("Date", "")),
            plot_mode=data.get("plot_mode", PLOT_MODE_DUAL),
            project_type=data.get("project_type", PROJECT_TYPE_MIXED),
            building_config=data.get("building_config", "G+7"),
            building_height_m=float(data.get("building_height_m", 0) or 0),
            num_wings=int(data.get("num_wings", 1) or 1),
            building_type=data.get("building_type", "Residential Apartment"),
            client_address=data.get("client_address", ""),
            client_contact=data.get("client_contact", ""),
            client_email=data.get("client_email", ""),
            client_gst=data.get("client_gst", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            rainfall_zone=data.get("rainfall_zone", ""),
            climate=data.get("climate", ""),
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
