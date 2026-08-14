"""Project lifecycle helpers — new, open, search, auto ID."""

from __future__ import annotations

import os
from datetime import datetime

from config.nbc_2026 import PROJECT_TYPE_UNSET
from models.project import ProjectData, RevisionInfo
from services.database import (
    DB_PATH,
    delete_project,
    get_dashboard_projects,
    get_project_history,
    get_project_summary,
    get_project_workflow_row,
    load_project_from_db,
    log_audit_event,
    parse_project_snapshot,
    project_exists,
    save_project,
    search_projects,
    update_project_workflow,
)
from services.project_workflow import completion_fields_on_finish, open_fields_on_start
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


def create_new_project_state(db_path: str = DB_PATH) -> AppState:
    """Fresh project with auto-generated IDs."""
    state = AppState()
    state.project = ProjectData(
        project_id=generate_project_id(db_path),
        project_name="NEW PROJECT",
        client_name="",
        project_location="",
        project_type=PROJECT_TYPE_UNSET,
        engineer_name="",
        project_no=next_project_number(db_path),
        date=datetime.now().strftime("%d-%m-%Y"),
        revision=RevisionInfo(
            date=datetime.now().strftime("%d-%m-%Y"),
            prepared_by="",
        ),
    )
    state.residential = []
    state.commercial = []
    return state


def load_project_state(project_id: str, db_path: str = DB_PATH) -> AppState:
    """Load an existing project into AppState."""
    summary = get_project_summary(project_id, db_path)
    if not summary:
        raise ValueError(f"Project not found: {project_id}")
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


def persist_project_state(state: AppState, db_path: str = DB_PATH) -> bool:
    """Save project; returns True if updated existing, False if new."""
    result = save_project(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
        db_path=db_path,
    )
    invalidate_dashboard_cache()
    return result


def find_projects(query: str = "", limit: int = 50, db_path: str = DB_PATH):
    """Search/list projects by ID, name, client, location, type, or date."""
    if query:
        return search_projects(query, limit=limit, db_path=db_path)
    return get_project_history(limit, db_path)


def list_dashboard_projects(db_path: str = DB_PATH):
    return get_dashboard_projects(db_path=db_path)


_dashboard_cache: dict = {"rows": None, "mtime": 0.0}


def list_dashboard_projects_cached(db_path: str = DB_PATH):
    """Return dashboard rows, using a lightweight file-mtime cache."""
    try:
        mtime = os.path.getmtime(db_path) if os.path.exists(db_path) else 0.0
    except OSError:
        mtime = 0.0
    if _dashboard_cache["rows"] is not None and _dashboard_cache["mtime"] == mtime:
        return _dashboard_cache["rows"]
    rows = get_dashboard_projects(db_path=db_path)
    _dashboard_cache["rows"] = rows
    _dashboard_cache["mtime"] = mtime
    return rows


def invalidate_dashboard_cache() -> None:
    _dashboard_cache["rows"] = None
    _dashboard_cache["mtime"] = 0.0


def mark_project_opened(project_id: str, db_path: str = DB_PATH) -> None:
    row = get_project_workflow_row(project_id, db_path)
    if not row:
        return
    updates = open_fields_on_start(row)
    if updates:
        update_project_workflow(project_id, updates, db_path)


def mark_project_completed(project_id: str, db_path: str = DB_PATH) -> None:
    row = get_project_workflow_row(project_id, db_path)
    if not row:
        return
    updates = completion_fields_on_finish(row)
    update_project_workflow(project_id, updates, db_path)


def remove_project(project_id: str, *, username: str = "", db_path: str = DB_PATH) -> bool:
    result = delete_project(project_id, username=username, db_path=db_path)
    if result:
        invalidate_dashboard_cache()
    return result
