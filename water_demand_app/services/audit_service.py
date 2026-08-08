"""Audit log — records project and user lifecycle events."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.database import DB_PATH, init_db

ACTION_PROJECT_CREATED = "project_created"
ACTION_PROJECT_ASSIGNED = "project_assigned"
ACTION_PROJECT_OPENED = "project_opened"
ACTION_PROJECT_UPDATED = "project_updated"
ACTION_PROJECT_COMPLETED = "project_completed"
ACTION_PROJECT_PAUSED = "project_paused"
ACTION_PROJECT_RESUMED = "project_resumed"
ACTION_PROJECT_APPROVED = "project_approved"
ACTION_PROJECT_REJECTED = "project_rejected"
ACTION_PROJECT_DELETED = "project_deleted"
ACTION_USER_CREATED = "user_created"
ACTION_USER_UPDATED = "user_updated"
ACTION_USER_DEACTIVATED = "user_deactivated"


def init_audit_table(db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT DEFAULT '',
            user_id INTEGER DEFAULT 0,
            username TEXT DEFAULT '',
            action TEXT NOT NULL,
            field_name TEXT DEFAULT '',
            old_value TEXT DEFAULT '',
            new_value TEXT DEFAULT '',
            timestamp TEXT NOT NULL,
            reason TEXT DEFAULT ''
        )
        """
    )
    conn.commit()
    conn.close()


def log_audit(
    action: str,
    username: str = "",
    user_id: int = 0,
    project_id: str = "",
    field_name: str = "",
    old_value: str = "",
    new_value: str = "",
    reason: str = "",
    db_path: str = DB_PATH,
) -> None:
    init_audit_table(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audit_logs
        (project_id, user_id, username, action, field_name, old_value, new_value, timestamp, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_id,
            user_id,
            username,
            action,
            field_name,
            old_value,
            new_value,
            datetime.now().isoformat(),
            reason,
        ),
    )
    conn.commit()
    conn.close()


def list_audit_logs(
    project_id: str = "",
    limit: int = 200,
    db_path: str = DB_PATH,
) -> List[Dict[str, Any]]:
    init_audit_table(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    if project_id:
        cur.execute(
            """
            SELECT id, project_id, user_id, username, action, field_name, old_value, new_value, timestamp, reason
            FROM audit_logs WHERE project_id = ? ORDER BY timestamp DESC LIMIT ?
            """,
            (project_id, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, project_id, user_id, username, action, field_name, old_value, new_value, timestamp, reason
            FROM audit_logs ORDER BY timestamp DESC LIMIT ?
            """,
            (limit,),
        )
    rows = [
        {
            "id": r[0],
            "project_id": r[1],
            "user_id": r[2],
            "username": r[3],
            "action": r[4],
            "field_name": r[5],
            "old_value": r[6],
            "new_value": r[7],
            "timestamp": r[8],
            "reason": r[9],
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return rows
