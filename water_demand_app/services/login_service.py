"""Login validation with role matching and employee-ID lookup."""

from __future__ import annotations

from typing import Optional, Tuple

from models.user import ROLE_LABELS, UserSession
from services.audit_service import (
    ACTION_LOGIN_FAILED,
    ACTION_LOGIN_SUCCESS,
    log_audit,
)
from services.auth_db import _USER_SELECT, _conn, _row_to_session, init_users_table, verify_password
from services.database import DB_PATH

ROLE_LABEL_TO_KEY = {label: key for key, label in ROLE_LABELS.items()}
ROLE_KEY_TO_LABEL = ROLE_LABELS


def lookup_user_row(identifier: str, db_path: str = DB_PATH) -> Optional[tuple]:
    """Find user by username or employee ID (case-insensitive)."""
    init_users_table(db_path)
    key = (identifier or "").strip()
    if not key:
        return None
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        _USER_SELECT + " WHERE LOWER(username) = ? OR UPPER(employee_id) = ?",
        (key.lower(), key.upper()),
    )
    row = cur.fetchone()
    conn.close()
    return row


def authenticate_with_role(
    identifier: str,
    password: str,
    selected_role_label: str,
    db_path: str = DB_PATH,
) -> Tuple[Optional[UserSession], str]:
    """
    Validate credentials and ensure selected role matches database role.
    Returns (UserSession, error_message). error_message is empty on success.
    """
    from datetime import datetime

    identifier = (identifier or "").strip()
    password = password or ""
    role_label = (selected_role_label or "").strip()

    if not identifier:
        return None, "Please enter username."
    if not password:
        return None, "Please enter password."
    if not role_label or role_label == "Select Role":
        return None, "Please select your role."

    expected_role = ROLE_LABEL_TO_KEY.get(role_label)
    if not expected_role:
        return None, "Please select your role."

    row = lookup_user_row(identifier, db_path)
    if not row or not row[5]:
        log_audit(
            ACTION_LOGIN_FAILED,
            username=identifier,
            reason=f"role={role_label}",
            db_path=db_path,
        )
        return None, "Invalid username, password, or role."

    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT salt, password_hash FROM users WHERE user_id = ?", (row[0],))
    cred = cur.fetchone()
    if not cred or not verify_password(password, cred[0], cred[1]):
        conn.close()
        log_audit(
            ACTION_LOGIN_FAILED,
            username=row[1],
            user_id=row[0],
            reason=f"role={role_label}",
            db_path=db_path,
        )
        return None, "Invalid username, password, or role."
    conn.close()

    user = _row_to_session(row)
    if user.role != expected_role:
        log_audit(
            ACTION_LOGIN_FAILED,
            username=user.username,
            user_id=user.user_id,
            reason=f"role_mismatch selected={role_label} actual={ROLE_KEY_TO_LABEL.get(user.role, user.role)}",
            db_path=db_path,
        )
        return None, "Invalid username, password, or role."

    now = datetime.now().isoformat()
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now, user.user_id))
    conn.commit()
    conn.close()

    log_audit(
        ACTION_LOGIN_SUCCESS,
        username=user.username,
        user_id=user.user_id,
        reason=ROLE_KEY_TO_LABEL.get(user.role, user.role),
        db_path=db_path,
    )
    return user, ""
