"""Project lifecycle helpers — new, open, search, auto ID."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from models.project import ProjectData, RevisionInfo
from models.user import UserSession
from services.database import (
    DB_PATH,
    load_project_from_db,
    parse_project_snapshot,
    project_exists,
    save_project,
    search_projects,
)
from services.lookup_db import next_project_number
from ui.app_state import AppState


def generate_project_id(db_path: str = DB_PATH) -> str:
    """Auto-generate unique project ID: WD-YYYYMMDD-NNN."""
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"WD-{today}-"
    seq = 1
    while True:
        candidate = f"{prefix}{seq:03d}"
        if not project_exists(candidate, db_path):
            return candidate
        seq += 1
        if seq > 999:
            return f"WD-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def create_new_project_state(user: Optional[UserSession] = None, db_path: str = DB_PATH) -> AppState:
    """Fresh project with auto-generated IDs."""
    state = AppState()
    state.project = ProjectData(
        project_id=generate_project_id(db_path),
        project_name="NEW PROJECT",
        client_name="",
        project_location="",
        engineer_name=user.full_name if user else "Akash",
        project_no=next_project_number(db_path),
        date=datetime.now().strftime("%d-%m-%Y"),
        revision=RevisionInfo(
            date=datetime.now().strftime("%d-%m-%Y"),
            prepared_by=user.full_name if user else "",
        ),
    )
    state.residential = []
    state.commercial = []
    return state


def load_project_state(project_id: str, db_path: str = DB_PATH) -> AppState:
    """Load an existing project into AppState."""
    data = load_project_from_db(project_id, db_path)
    project, residential, commercial, other, calculated = parse_project_snapshot(data)
    state = AppState()
    state.project = project
    state.residential = residential
    state.commercial = commercial
    state.other = other
    if calculated:
        state.run_calculations()
    else:
        state.auto_calculate()
    return state


def persist_project_state(
    state: AppState,
    user: Optional[UserSession] = None,
    db_path: str = DB_PATH,
) -> bool:
    """Save project; returns True if updated existing, False if new."""
    username = user.username if user else ""
    return save_project(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
        db_path=db_path,
        created_by=username,
        updated_by=username,
    )


def find_projects(query: str = "", limit: int = 50, db_path: str = DB_PATH):
    return search_projects(query, limit=limit, db_path=db_path)
