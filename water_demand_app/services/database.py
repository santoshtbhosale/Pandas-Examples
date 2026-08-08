from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from models.commercial import CommercialUnit
from models.other_details import OtherDetails
from models.project import ProjectData
from models.residential import ResidentialWing


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "water_demand.db")
JSON_SCHEMA_VERSION = "1.0"


def init_db(db_path: str = DB_PATH) -> None:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            project_id TEXT PRIMARY KEY,
            project_name TEXT,
            client_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            project_no TEXT,
            date TEXT,
            revision_no TEXT,
            description TEXT,
            prepared_by TEXT,
            checked_by TEXT,
            approved_by TEXT,
            total_water_demand REAL,
            stp_capacity_a REAL,
            stp_capacity_b REAL,
            json_snapshot TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS residential_wings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            plot TEXT,
            wing_name TEXT,
            flats INTEGER,
            pop_per_flat INTEGER,
            sort_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS commercial_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT,
            plot TEXT,
            block_name TEXT,
            comm_type TEXT,
            floor_label TEXT,
            area_sqm REAL,
            density_override REAL,
            sort_order INTEGER,
            FOREIGN KEY (project_id) REFERENCES projects(project_id)
        )
        """
    )
    conn.commit()
    conn.close()


def save_project(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    snapshot = build_project_snapshot(project, residential, commercial, other, calculated)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    stp_a = 0.0
    stp_b = 0.0
    total_water = 0.0
    if calculated:
        stp_a = float(calculated.get("plots", {}).get("Plot-A", {}).get("STP Capacity (KLD)", 0))
        stp_b = float(calculated.get("plots", {}).get("Plot-B", {}).get("STP Capacity (KLD)", 0))
        total_water = float(calculated.get("total", {}).get("Total Water (LPD)", 0))

    cursor.execute(
        """
        INSERT OR REPLACE INTO projects (
            project_id, project_name, client_name, project_location, engineer_name,
            project_no, date, revision_no, description, prepared_by, checked_by,
            approved_by, total_water_demand, stp_capacity_a, stp_capacity_b,
            json_snapshot, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM projects WHERE project_id = ?), ?
        ), ?)
        """,
        (
            project.project_id,
            project.project_name,
            project.client_name,
            project.project_location,
            project.engineer_name,
            project.project_no,
            project.date,
            project.revision.revision_no,
            project.revision.description,
            project.revision.prepared_by,
            project.revision.checked_by,
            project.revision.approved_by,
            total_water,
            stp_a,
            stp_b,
            json.dumps(snapshot),
            project.project_id,
            now,
            now,
        ),
    )
    cursor.execute("DELETE FROM residential_wings WHERE project_id = ?", (project.project_id,))
    cursor.execute("DELETE FROM commercial_units WHERE project_id = ?", (project.project_id,))
    for idx, wing in enumerate(residential):
        cursor.execute(
            """
            INSERT INTO residential_wings
            (project_id, plot, wing_name, flats, pop_per_flat, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (project.project_id, wing.plot, wing.wing, wing.flats, wing.pop_per_flat, idx),
        )
    for idx, unit in enumerate(commercial):
        cursor.execute(
            """
            INSERT INTO commercial_units
            (project_id, plot, block_name, comm_type, floor_label, area_sqm, density_override, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                project.project_id,
                unit.plot,
                unit.block,
                unit.comm_type,
                unit.floor_label,
                unit.area_sqm,
                unit.density_override,
                idx,
            ),
        )
    conn.commit()
    conn.close()


def list_projects(db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT project_id, project_name, client_name, date FROM projects ORDER BY updated_at DESC"
    )
    rows = [
        {"project_id": r[0], "project_name": r[1], "client_name": r[2], "date": r[3]}
        for r in cursor.fetchall()
    ]
    conn.close()
    return rows


def load_project_from_db(project_id: str, db_path: str = DB_PATH) -> Dict[str, Any]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT json_snapshot FROM projects WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Project not found: {project_id}")
    return json.loads(row[0])


def build_project_snapshot(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": JSON_SCHEMA_VERSION,
        "project": project.to_dict(),
        "residential": [r.to_dict() for r in residential],
        "commercial": [c.to_dict() for c in commercial],
        "other": other.to_dict(),
        "calculated": calculated or {},
    }


def parse_project_snapshot(data: Dict[str, Any]) -> tuple:
    project = ProjectData.from_dict(data.get("project", {}))
    residential = [ResidentialWing.from_dict(r) for r in data.get("residential", [])]
    commercial = [CommercialUnit.from_dict(c) for c in data.get("commercial", [])]
    other = OtherDetails.from_dict(data.get("other", {}))
    calculated = data.get("calculated", {})
    return project, residential, commercial, other, calculated
