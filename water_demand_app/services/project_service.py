"""Project lifecycle helpers — new, open, search, auto ID."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from config.nbc_2026 import PROJECT_TYPE_UNSET
from models.project import ProjectData, RevisionInfo
from models.user import UserSession
from services.database import (
    DB_PATH,
    get_project_summary,
    load_project_from_db,
    parse_project_snapshot,
    project_exists,
    save_project,
)
from services.audit_service import ACTION_PROJECT_CREATED, ACTION_PROJECT_UPDATED, log_audit
from services.lookup_db import next_project_number
from services.project_workflow_service import (
    get_project_workflow,
    record_project_opened,
    search_project_records,
    update_project_workflow,
    user_can_access_project_record,
)
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
        project_type=PROJECT_TYPE_UNSET,
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


def load_project_state(
    project_id: str,
    db_path: str = DB_PATH,
    user: Optional[UserSession] = None,
) -> AppState:
    """Load an existing project into AppState."""
    records = search_project_records(query=project_id, limit=1, db_path=db_path, user=user)
    record = next((r for r in records if r["project_id"] == project_id), None)
    if not record:
        summary = get_project_summary(project_id, db_path)
        if not summary:
            raise ValueError(f"Project not found: {project_id}")
        if user and not user.can_access_project(
            summary.get("created_by", ""),
            summary.get("engineer_name", ""),
        ):
            raise ValueError("You do not have permission to open this project.")
    elif user and not user_can_access_project_record(user, record, db_path):
        raise ValueError("You do not have permission to open this project.")
    if user:
        record_project_opened(project_id, user, db_path)
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
    is_update = project_exists(state.project.project_id, db_path)
    result = save_project(
        state.project,
        state.residential,
        state.commercial,
        state.other,
        state.results.to_dict() if state.results else None,
        db_path=db_path,
        created_by=username,
        updated_by=username,
    )
    wf = get_project_workflow(state.project.project_id, db_path)
    if not wf.project_type:
        wf.project_type = state.project.project_type
        update_project_workflow(state.project.project_id, wf, db_path)
    if user:
        action = ACTION_PROJECT_UPDATED if is_update else ACTION_PROJECT_CREATED
        log_audit(action, user.username, user.user_id, state.project.project_id, db_path=db_path)
    return result


def find_projects(
    query: str = "",
    limit: int = 50,
    db_path: str = DB_PATH,
    user: Optional[UserSession] = None,
    status_filter: str = "",
    date_from: str = "",
    date_to: str = "",
):
    return search_project_records(
        query=query,
        limit=limit,
        db_path=db_path,
        user=user,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
    )
