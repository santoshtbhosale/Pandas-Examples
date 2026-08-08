"""Project workflow persistence — assignment, timer, status."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from models.project_workflow import (
    DURATION_PRESETS_MINUTES,
    STATUS_IN_PROGRESS,
    STATUS_NOT_STARTED,
    STATUS_PAUSED,
    ProjectWorkflow,
)
from models.user import UserSession
from services.audit_service import (
    ACTION_PROJECT_ASSIGNED,
    ACTION_PROJECT_COMPLETED,
    ACTION_PROJECT_OPENED,
    ACTION_PROJECT_PAUSED,
    ACTION_PROJECT_RESUMED,
    ACTION_PROJECT_UPDATED,
    log_audit,
)
from services.auth_db import get_user_by_username, list_team_engineers
from services.database import DB_PATH, init_db, load_project_from_db, save_project
from services.database import parse_project_snapshot, project_exists
from services.project_timer import compute_completion, timer_snapshot


WORKFLOW_COLUMNS = (
    "project_type",
    "assigned_to_username",
    "assigned_by_username",
    "team_leader_id",
    "assigned_at",
    "expected_completion_at",
    "project_opened_at",
    "completed_at",
    "paused_at",
    "total_paused_seconds",
    "priority",
    "status",
    "progress_pct",
    "delay_seconds",
    "total_time_taken_seconds",
    "completion_outcome",
    "assigned_duration_minutes",
)


def ensure_workflow_schema(db_path: str = DB_PATH) -> None:
    init_db(db_path)


def _wf_from_row(row: tuple, offset: int = 10) -> ProjectWorkflow:
    return ProjectWorkflow(
        project_type=row[offset] or "",
        assigned_to_username=row[offset + 1] or "",
        assigned_by_username=row[offset + 2] or "",
        team_leader_id=int(row[offset + 3] or 0),
        assigned_at=row[offset + 4] or "",
        expected_completion_at=row[offset + 5] or "",
        project_opened_at=row[offset + 6] or "",
        completed_at=row[offset + 7] or "",
        paused_at=row[offset + 8] or "",
        total_paused_seconds=int(row[offset + 9] or 0),
        priority=row[offset + 10] or "Normal",
        status=row[offset + 11] or STATUS_NOT_STARTED,
        progress_pct=int(row[offset + 12] or 0),
        delay_seconds=int(row[offset + 13] or 0),
        total_time_taken_seconds=int(row[offset + 14] or 0),
        completion_outcome=row[offset + 15] or "",
        assigned_duration_minutes=int(row[offset + 16] or 0),
    )


PROJECT_LIST_SQL = """
    SELECT project_id, project_name, client_name, project_location, project_no,
           date, updated_at, total_water_demand, engineer_name, created_by,
           project_type, assigned_to_username, assigned_by_username, team_leader_id,
           assigned_at, expected_completion_at, project_opened_at, completed_at,
           paused_at, total_paused_seconds, priority, status, progress_pct,
           delay_seconds, total_time_taken_seconds, completion_outcome, assigned_duration_minutes
    FROM projects
"""


def _row_to_project_record(row: tuple) -> Dict[str, Any]:
    wf = _wf_from_row(row, 10)
    snap = timer_snapshot(wf)
    return {
        "project_id": row[0] or "",
        "project_name": row[1] or "",
        "client_name": row[2] or "",
        "project_location": row[3] or "",
        "project_no": row[4] or "",
        "date": row[5] or "",
        "updated_at": row[6] or "",
        "total_water_demand": str(row[7] or 0),
        "engineer_name": row[8] or "",
        "created_by": row[9] or "",
        "project_type": wf.project_type,
        "assigned_to_username": wf.assigned_to_username,
        "assigned_by_username": wf.assigned_by_username,
        "team_leader_id": wf.team_leader_id,
        "assigned_at": wf.assigned_at,
        "expected_completion_at": wf.expected_completion_at,
        "project_opened_at": wf.project_opened_at,
        "completed_at": wf.completed_at,
        "priority": wf.priority,
        "status": snap["status"],
        "progress_pct": wf.progress_pct,
        "completion_outcome": snap["completion_outcome"],
        "elapsed_display": snap["elapsed_display"],
        "remaining_display": snap["remaining_display"],
        "delay_display": snap["delay_display"],
    }


def get_project_workflow(project_id: str, db_path: str = DB_PATH) -> ProjectWorkflow:
    ensure_workflow_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(PROJECT_LIST_SQL + " WHERE project_id = ?", (project_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return ProjectWorkflow()
    return _wf_from_row(row, 10)


def update_project_workflow(project_id: str, wf: ProjectWorkflow, db_path: str = DB_PATH) -> None:
    ensure_workflow_schema(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE projects SET
            project_type = ?, assigned_to_username = ?, assigned_by_username = ?,
            team_leader_id = ?, assigned_at = ?, expected_completion_at = ?,
            project_opened_at = ?, completed_at = ?, paused_at = ?,
            total_paused_seconds = ?, priority = ?, status = ?, progress_pct = ?,
            delay_seconds = ?, total_time_taken_seconds = ?, completion_outcome = ?,
            assigned_duration_minutes = ?, updated_at = ?
        WHERE project_id = ?
        """,
        (
            wf.project_type,
            wf.assigned_to_username,
            wf.assigned_by_username,
            wf.team_leader_id,
            wf.assigned_at,
            wf.expected_completion_at,
            wf.project_opened_at,
            wf.completed_at,
            wf.paused_at,
            wf.total_paused_seconds,
            wf.priority,
            wf.status,
            wf.progress_pct,
            wf.delay_seconds,
            wf.total_time_taken_seconds,
            wf.completion_outcome,
            wf.assigned_duration_minutes,
            datetime.now().isoformat(),
            project_id,
        ),
    )
    conn.commit()
    conn.close()


def _team_engineer_usernames(user: UserSession, db_path: str) -> List[str]:
    if user.is_team_leader():
        return [e.username for e in list_team_engineers(user.user_id, db_path)]
    return []


def user_can_access_project_record(user: UserSession, record: Dict[str, Any], db_path: str = DB_PATH) -> bool:
    team_usernames = _team_engineer_usernames(user, db_path)
    return user.can_access_project(
        created_by=record.get("created_by", ""),
        engineer_name=record.get("engineer_name", ""),
        assigned_to_username=record.get("assigned_to_username", ""),
        team_leader_id=int(record.get("team_leader_id", 0) or 0),
        team_engineer_ids=team_usernames,
    )


def search_project_records(
    query: str = "",
    limit: int = 100,
    db_path: str = DB_PATH,
    user: Optional[UserSession] = None,
    status_filter: str = "",
    date_from: str = "",
    date_to: str = "",
) -> List[Dict[str, Any]]:
    ensure_workflow_schema(db_path)
    conditions: list[str] = []
    params: list = []
    if user:
        if user.is_engineer():
            conditions.append(
                "(assigned_to_username = ? OR created_by = ? OR "
                "(COALESCE(created_by, '') = '' AND LOWER(engineer_name) = LOWER(?)))"
            )
            params.extend([user.username, user.username, user.full_name])
        elif user.is_team_leader():
            engineers = _team_engineer_usernames(user, db_path)
            if engineers:
                placeholders = ",".join("?" * len(engineers))
                conditions.append(
                    f"(team_leader_id = ? OR assigned_to_username IN ({placeholders}))"
                )
                params.append(user.user_id)
                params.extend(engineers)
            else:
                conditions.append("team_leader_id = ?")
                params.append(user.user_id)
    key = (query or "").strip()
    if key:
        like = f"%{key}%"
        conditions.append(
            "(project_id LIKE ? OR project_name LIKE ? OR client_name LIKE ? "
            "OR engineer_name LIKE ? OR project_type LIKE ? OR status LIKE ?)"
        )
        params.extend([like, like, like, like, like, like])
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if date_from:
        conditions.append("date(assigned_at) >= date(?)")
        params.append(date_from)
    if date_to:
        conditions.append("date(assigned_at) <= date(?)")
        params.append(date_to)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(PROJECT_LIST_SQL + where + " ORDER BY updated_at DESC LIMIT ?", tuple(params) + (limit,))
    rows = [_row_to_project_record(r) for r in cur.fetchall()]
    conn.close()
    if user and not user.is_admin_level() and not user.is_team_leader() and not user.is_engineer():
        return [r for r in rows if user_can_access_project_record(user, r, db_path)]
    return rows


def assign_project(
    project_id: str,
    engineer_username: str,
    assigner: UserSession,
    duration_label: str = "2 Hours",
    custom_minutes: int = 0,
    priority: str = "Normal",
    db_path: str = DB_PATH,
) -> None:
    engineer = get_user_by_username(engineer_username, db_path)
    if not engineer:
        raise ValueError(f"Engineer not found: {engineer_username}")
    minutes = custom_minutes if duration_label == "Custom" else DURATION_PRESETS_MINUTES.get(duration_label, custom_minutes or 120)
    now = datetime.now()
    expected = now + timedelta(minutes=minutes)
    wf = get_project_workflow(project_id, db_path)
    wf.assigned_to_username = engineer.username
    wf.assigned_by_username = assigner.username
    wf.team_leader_id = assigner.user_id if assigner.is_team_leader() else int(engineer.team_leader_id or 0)
    wf.assigned_at = now.isoformat()
    wf.expected_completion_at = expected.isoformat()
    wf.assigned_duration_minutes = minutes
    wf.priority = priority
    wf.status = STATUS_NOT_STARTED
    wf.progress_pct = 0
    data = load_project_from_db(project_id, db_path)
    project, residential, commercial, other, calculated = parse_project_snapshot(data)
    wf.project_type = project.project_type
    project.engineer_name = engineer.full_name
    save_project(
        project, residential, commercial, other, calculated,
        db_path=db_path, created_by=engineer.username, updated_by=assigner.username,
    )
    update_project_workflow(project_id, wf, db_path)
    log_audit(
        ACTION_PROJECT_ASSIGNED, assigner.username, assigner.user_id, project_id,
        field_name="assigned_to", new_value=engineer.username,
        reason=f"Expected completion: {expected.isoformat()}",
        db_path=db_path,
    )


def record_project_opened(project_id: str, user: UserSession, db_path: str = DB_PATH) -> ProjectWorkflow:
    wf = get_project_workflow(project_id, db_path)
    now = datetime.now().isoformat()
    if not wf.project_opened_at:
        wf.project_opened_at = now
    if wf.status == STATUS_NOT_STARTED:
        wf.status = STATUS_IN_PROGRESS
        wf.progress_pct = max(wf.progress_pct, 10)
    update_project_workflow(project_id, wf, db_path)
    log_audit(ACTION_PROJECT_OPENED, user.username, user.user_id, project_id, db_path=db_path)
    return wf


def pause_project(project_id: str, user: UserSession, db_path: str = DB_PATH) -> ProjectWorkflow:
    wf = get_project_workflow(project_id, db_path)
    if wf.status != STATUS_IN_PROGRESS:
        return wf
    wf.status = STATUS_PAUSED
    wf.paused_at = datetime.now().isoformat()
    update_project_workflow(project_id, wf, db_path)
    log_audit(ACTION_PROJECT_PAUSED, user.username, user.user_id, project_id, db_path=db_path)
    return wf


def resume_project(project_id: str, user: UserSession, db_path: str = DB_PATH) -> ProjectWorkflow:
    wf = get_project_workflow(project_id, db_path)
    if wf.status != STATUS_PAUSED or not wf.paused_at:
        return wf
    paused_at = datetime.fromisoformat(wf.paused_at)
    wf.total_paused_seconds += int((datetime.now() - paused_at).total_seconds())
    wf.paused_at = ""
    wf.status = STATUS_IN_PROGRESS
    update_project_workflow(project_id, wf, db_path)
    log_audit(ACTION_PROJECT_RESUMED, user.username, user.user_id, project_id, db_path=db_path)
    return wf


def complete_project(project_id: str, user: UserSession, db_path: str = DB_PATH) -> ProjectWorkflow:
    wf = get_project_workflow(project_id, db_path)
    wf = compute_completion(wf)
    update_project_workflow(project_id, wf, db_path)
    log_audit(
        ACTION_PROJECT_COMPLETED, user.username, user.user_id, project_id,
        new_value=wf.completion_outcome, db_path=db_path,
    )
    return wf


def log_field_change(
    project_id: str,
    user: UserSession,
    field_name: str,
    old_value: str,
    new_value: str,
    db_path: str = DB_PATH,
) -> None:
    if str(old_value) == str(new_value):
        return
    log_audit(
        ACTION_PROJECT_UPDATED, user.username, user.user_id, project_id,
        field_name=field_name, old_value=str(old_value), new_value=str(new_value),
        db_path=db_path,
    )


def dashboard_stats(user: Optional[UserSession] = None, db_path: str = DB_PATH) -> Dict[str, int]:
    records = search_project_records(limit=500, db_path=db_path, user=user)
    today = datetime.now().date().isoformat()
    stats = {
        "total": len(records),
        "today": 0,
        "in_progress": 0,
        "completed": 0,
        "pending": 0,
        "delayed": 0,
        "pending_approval": 0,
    }
    for r in records:
        assigned = (r.get("assigned_at") or "")[:10]
        if assigned == today:
            stats["today"] += 1
        status = r.get("status", "")
        if status in ("in_progress", "paused"):
            stats["in_progress"] += 1
        elif status == "completed":
            stats["completed"] += 1
        elif status == "not_started":
            stats["pending"] += 1
        elif status == "delayed":
            stats["delayed"] += 1
        elif status == "pending_approval":
            stats["pending_approval"] += 1
    return stats


def engineer_performance(team_leader_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    engineers = list_team_engineers(team_leader_id, db_path)
    results = []
    for eng in engineers:
        records = search_project_records(limit=500, db_path=db_path)
        mine = [r for r in records if r.get("assigned_to_username") == eng.username]
        completed = [r for r in mine if r.get("status") == "completed"]
        in_prog = [r for r in mine if r.get("status") in ("in_progress", "paused")]
        delayed = [r for r in mine if r.get("status") == "delayed"]
        early = sum(1 for r in completed if r.get("completion_outcome") == "completed_early")
        on_time = sum(1 for r in completed if r.get("completion_outcome") == "completed_on_time")
        late = sum(1 for r in completed if r.get("completion_outcome") == "completed_late")
        results.append({
            "engineer_name": eng.full_name,
            "username": eng.username,
            "assigned": len(mine),
            "completed": len(completed),
            "in_progress": len(in_prog),
            "delayed": len(delayed),
            "early": early,
            "on_time": on_time,
            "late": late,
        })
    return results
