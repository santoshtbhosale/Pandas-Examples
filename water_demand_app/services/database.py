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

_HISTORY_SQL = """
    SELECT project_id, project_name, client_name, project_location, project_no,
           date, updated_at, total_water_demand, engineer_name, created_by
    FROM projects
"""


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
            updated_at TEXT,
            created_by TEXT DEFAULT '',
            updated_by TEXT DEFAULT ''
        )
        """
    )
    _migrate_projects_table(cursor)
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


def _migrate_projects_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("PRAGMA table_info(projects)")
    cols = {row[1] for row in cursor.fetchall()}
    if "created_by" not in cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN created_by TEXT DEFAULT ''")
    if "updated_by" not in cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN updated_by TEXT DEFAULT ''")


def project_exists(project_id: str, db_path: str = DB_PATH) -> bool:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM projects WHERE project_id = ?", (project_id,))
    found = cursor.fetchone() is not None
    conn.close()
    return found


def save_project(
    project: ProjectData,
    residential: List[ResidentialWing],
    commercial: List[CommercialUnit],
    other: OtherDetails,
    calculated: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH,
    created_by: str = "",
    updated_by: str = "",
) -> bool:
    init_db(db_path)
    is_update = project_exists(project.project_id, db_path)
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
            json_snapshot, created_at, updated_at, created_by, updated_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM projects WHERE project_id = ?), ?
        ), ?, COALESCE(
            (SELECT created_by FROM projects WHERE project_id = ?), ?
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
            project.project_id,
            created_by or updated_by,
            updated_by or created_by,
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
    return is_update


def _row_to_summary(row: tuple) -> Dict[str, str]:
    return {
        "project_id": row[0] or "",
        "project_name": row[1] or "",
        "client_name": row[2] or "",
        "project_location": row[3] or "",
        "project_no": row[4] or "",
        "date": row[5] or "",
        "updated_at": row[6] or "",
        "total_water_demand": str(row[7] or 0),
        "engineer_name": row[8] or "" if len(row) > 8 else "",
        "created_by": row[9] or "" if len(row) > 9 else "",
    }


def get_project_history(limit: int = 100, db_path: str = DB_PATH) -> List[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        _HISTORY_SQL + " ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    )
    rows = [_row_to_summary(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def search_projects(
    query: str,
    limit: int = 50,
    db_path: str = DB_PATH,
    *,
    username: str = "",
    role: str = "",
    full_name: str = "",
) -> List[Dict[str, str]]:
    init_db(db_path)
    key = f"%{(query or '').strip()}%"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    conditions: list[str] = []
    params: list = []
    if role == "engineer" and username:
        conditions.append(
            "(created_by = ? OR (COALESCE(created_by, '') = '' AND LOWER(engineer_name) = LOWER(?)))"
        )
        params.extend([username, full_name or username])
    if key != "%%":
        conditions.append(
            "(project_id LIKE ? OR project_name LIKE ? OR client_name LIKE ? "
            "OR project_location LIKE ? OR project_no LIKE ? OR engineer_name LIKE ?)"
        )
        params.extend([key, key, key, key, key, key])
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    cursor.execute(
        _HISTORY_SQL + where + " ORDER BY updated_at DESC LIMIT ?",
        tuple(params) + (limit,),
    )
    rows = [_row_to_summary(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def get_project_summary(project_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, str]]:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(_HISTORY_SQL + " WHERE project_id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    return _row_to_summary(row) if row else None


def list_projects(db_path: str = DB_PATH) -> List[Dict[str, str]]:
    return get_project_history(200, db_path)


def update_project_metadata(
    project_id: str,
    project_name: str,
    client_name: str,
    project_location: str,
    engineer_name: str = "",
    updated_by: str = "",
    db_path: str = DB_PATH,
) -> None:
    """Update header fields on an existing project without touching calculation data."""
    init_db(db_path)
    data = load_project_from_db(project_id, db_path)
    project, residential, commercial, other, calculated = parse_project_snapshot(data)
    project.project_name = project_name
    project.client_name = client_name
    project.project_location = project_location
    if engineer_name:
        project.engineer_name = engineer_name
    save_project(
        project,
        residential,
        commercial,
        other,
        calculated,
        db_path=db_path,
        updated_by=updated_by,
    )


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
