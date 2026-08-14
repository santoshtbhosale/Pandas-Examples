"""SQLite persistence for Rain Water Harvesting projects (separate table)."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from rwh.models import RWHProjectData, RWHResults

# Prefer shared app data folder when available
_APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB = os.path.join(_APP_DIR, "data", "water_demand.db")


def _resolve_db_path(db_path: Optional[str] = None) -> str:
    if db_path:
        return db_path
    # Fallbacks used by consolidated main.py
    candidates = [
        os.path.join(os.path.dirname(_APP_DIR), "data", "water_demand.db"),
        os.path.join(os.path.dirname(_APP_DIR), "water_demand.db"),
        _DEFAULT_DB,
    ]
    for path in candidates:
        parent = os.path.dirname(path)
        if parent and (os.path.exists(path) or os.path.isdir(parent) or parent.endswith("data")):
            return path
    return _DEFAULT_DB


def init_rwh_db(db_path: Optional[str] = None) -> str:
    """Create RWH table in the shared SQLite database. Does not alter Water Demand tables."""
    path = _resolve_db_path(db_path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rwh_projects (
            rwh_id TEXT PRIMARY KEY,
            project_name TEXT,
            client_name TEXT,
            project_location TEXT,
            engineer_name TEXT,
            project_no TEXT,
            date TEXT,
            annual_rainfall_mm REAL,
            rainy_days INTEGER,
            max_daily_rainfall_mm REAL,
            collection_efficiency REAL,
            proposed_tank_liters REAL,
            annual_harvest_liters REAL,
            design_tank_liters REAL,
            notes TEXT,
            json_snapshot TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return path


def save_rwh_project(
    project: RWHProjectData,
    results: Optional[RWHResults] = None,
    db_path: Optional[str] = None,
) -> None:
    path = init_rwh_db(db_path)
    snapshot = {
        "project": project.to_dict(),
        "results": results.to_dict() if results else None,
    }
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    cursor.execute(
        """
        INSERT OR REPLACE INTO rwh_projects (
            rwh_id, project_name, client_name, project_location, engineer_name,
            project_no, date, annual_rainfall_mm, rainy_days, max_daily_rainfall_mm,
            collection_efficiency, proposed_tank_liters, annual_harvest_liters,
            design_tank_liters, notes, json_snapshot, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM rwh_projects WHERE rwh_id = ?), ?
        ), ?)
        """,
        (
            project.rwh_id,
            project.project_name,
            project.client_name,
            project.project_location,
            project.engineer_name,
            project.project_no,
            project.date,
            project.annual_rainfall_mm,
            project.rainy_days,
            project.max_daily_rainfall_mm,
            project.collection_efficiency,
            project.proposed_tank_liters,
            results.annual_harvest_liters if results else 0.0,
            results.design_tank_liters if results else 0.0,
            project.notes,
            json.dumps(snapshot),
            project.rwh_id,
            now,
            now,
        ),
    )
    conn.commit()
    conn.close()


def list_rwh_projects(db_path: Optional[str] = None) -> List[Dict[str, str]]:
    path = init_rwh_db(db_path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rwh_id, project_name, client_name, date, annual_harvest_liters, updated_at
        FROM rwh_projects
        ORDER BY updated_at DESC
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "rwh_id": r[0],
            "project_name": r[1] or "",
            "client_name": r[2] or "",
            "date": r[3] or "",
            "annual_harvest_liters": str(r[4] or 0),
            "updated_at": r[5] or "",
        }
        for r in rows
    ]


def load_rwh_project(rwh_id: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    path = init_rwh_db(db_path)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("SELECT json_snapshot FROM rwh_projects WHERE rwh_id = ?", (rwh_id,))
    row = cursor.fetchone()
    conn.close()
    if not row or not row[0]:
        raise ValueError(f"RWH project not found: {rwh_id}")
    return json.loads(row[0])
