from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing
from services.database import (
    JSON_SCHEMA_VERSION,
    build_project_snapshot,
    parse_project_snapshot,
    save_project,
)


def save_project_json(
    file_path: str,
    project: ProjectData,
    residential: list,
    commercial: list,
    other: OtherDetails,
    calculated: Dict[str, Any] | None = None,
) -> None:
    snapshot = build_project_snapshot(project, residential, commercial, other, calculated)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(snapshot, fh, indent=2, ensure_ascii=False)


def load_project_json(file_path: str) -> Tuple[ProjectData, list, list, OtherDetails, dict]:
    with open(file_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    version = data.get("schema_version", "1.0")
    if version != JSON_SCHEMA_VERSION:
        data["schema_version"] = JSON_SCHEMA_VERSION
    return parse_project_snapshot(data)


def export_to_database(
    project: ProjectData,
    residential: list,
    commercial: list,
    other: OtherDetails,
    calculated: Dict[str, Any] | None = None,
) -> None:
    save_project(project, residential, commercial, other, calculated)
