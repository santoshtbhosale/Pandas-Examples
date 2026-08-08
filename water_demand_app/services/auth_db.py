"""User authentication and administration — PBKDF2 password hashing."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime
from typing import List, Optional

from models.user import (
    ROLE_ADMIN,
    ROLE_ENGINEER,
    ROLE_SUPER_ADMIN,
    ROLE_TEAM_LEADER,
    ROLE_VIEWER,
    UserRecord,
    UserSession,
)
from services.database import DB_PATH, init_db

PBKDF2_ITERATIONS = 260_000


def _conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    init_db(db_path)
    return sqlite3.connect(db_path)


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(32)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, password_hash: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, computed = hash_password(password, salt)
    return secrets.compare_digest(computed, password_hash)


def _migrate_users_table(cur: sqlite3.Cursor) -> None:
    cur.execute("PRAGMA table_info(users)")
    cols = {row[1] for row in cur.fetchall()}
    for col, typedef in (
        ("employee_id", "TEXT DEFAULT ''"),
        ("team", "TEXT DEFAULT ''"),
        ("team_leader_id", "INTEGER DEFAULT 0"),
    ):
        if col not in cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typedef}")


def _row_to_session(row: tuple) -> UserSession:
    return UserSession(
        user_id=row[0],
        username=row[1],
        full_name=row[2],
        role=row[3],
        email=row[4] or "",
        employee_id=row[7] if len(row) > 7 else "",
        team=row[8] if len(row) > 8 else "",
        team_leader_id=int(row[9] or 0) if len(row) > 9 else 0,
    )


def _row_to_record(row: tuple) -> UserRecord:
    return UserRecord(
        user_id=row[0],
        username=row[1],
        full_name=row[2],
        role=row[3],
        email=row[4] or "",
        is_active=bool(row[5]),
        created_at=row[6] or "",
        employee_id=row[7] if len(row) > 7 else "",
        team=row[8] if len(row) > 8 else "",
        team_leader_id=int(row[9] or 0) if len(row) > 9 else 0,
    )


_USER_SELECT = """
    SELECT user_id, username, full_name, role, email, is_active, created_at,
           employee_id, team, team_leader_id
    FROM users
"""


def init_users_table(db_path: str = DB_PATH) -> None:
    init_db(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            last_login TEXT,
            employee_id TEXT DEFAULT '',
            team TEXT DEFAULT '',
            team_leader_id INTEGER DEFAULT 0
        )
        """
    )
    _migrate_users_table(cur)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        _seed_default_users(cur, conn)
    else:
        _ensure_super_admin_and_team_leader(cur, conn)
    conn.close()


def _seed_default_users(cur: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    now = datetime.now().isoformat()
    users = [
        ("superadmin", "Super@123", "Super Administrator", ROLE_SUPER_ADMIN, "super@americanedge.com", "EMP-001", "HQ", 0),
        ("admin", "Admin@123", "System Administrator", ROLE_ADMIN, "admin@americanedge.com", "EMP-002", "HQ", 0),
        ("leader", "Leader@123", "Team Leader", ROLE_TEAM_LEADER, "leader@americanedge.com", "EMP-TL1", "Design Team", 0),
        ("akash", "Akash@123", "Akash", ROLE_ENGINEER, "akash@americanedge.com", "EMP-101", "Design Team", 0),
        ("vaibhav", "Vaibhav@123", "Vaibhav", ROLE_ENGINEER, "vaibhav@americanedge.com", "EMP-102", "Design Team", 0),
        ("sachin", "Sachin@123", "Sachin", ROLE_ENGINEER, "sachin@americanedge.com", "EMP-103", "Design Team", 0),
        ("omkar", "Omkar@123", "Omkar", ROLE_VIEWER, "omkar@americanedge.com", "EMP-201", "HQ", 0),
    ]
    leader_id = 0
    for username, password, full_name, role, email, emp_id, team, tl_id in users:
        salt_hex, pwd_hash = hash_password(password)
        cur.execute(
            """
            INSERT INTO users
            (username, password_hash, salt, full_name, role, email, is_active, created_at,
             employee_id, team, team_leader_id)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
            """,
            (username, pwd_hash, salt_hex, full_name, role, email, now, emp_id, team, tl_id),
        )
        if role == ROLE_TEAM_LEADER:
            leader_id = cur.lastrowid
    if leader_id:
        for eng in ("akash", "vaibhav", "sachin"):
            cur.execute(
                "UPDATE users SET team_leader_id = ? WHERE username = ?",
                (leader_id, eng),
            )
    conn.commit()


def _ensure_super_admin_and_team_leader(cur: sqlite3.Cursor, conn: sqlite3.Connection) -> None:
    cur.execute("SELECT 1 FROM users WHERE role = ?", (ROLE_SUPER_ADMIN,))
    if not cur.fetchone():
        now = datetime.now().isoformat()
        salt_hex, pwd_hash = hash_password("Super@123")
        cur.execute(
            """
            INSERT INTO users
            (username, password_hash, salt, full_name, role, email, is_active, created_at, employee_id, team)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'EMP-001', 'HQ')
            """,
            ("superadmin", pwd_hash, salt_hex, "Super Administrator", ROLE_SUPER_ADMIN, "super@americanedge.com", now),
        )
    cur.execute("SELECT 1 FROM users WHERE role = ?", (ROLE_TEAM_LEADER,))
    if not cur.fetchone():
        now = datetime.now().isoformat()
        salt_hex, pwd_hash = hash_password("Leader@123")
        cur.execute(
            """
            INSERT INTO users
            (username, password_hash, salt, full_name, role, email, is_active, created_at, employee_id, team)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, 'EMP-TL1', 'Design Team')
            """,
            ("leader", pwd_hash, salt_hex, "Team Leader", ROLE_TEAM_LEADER, "leader@americanedge.com", now),
        )
        leader_id = cur.lastrowid
        for eng in ("akash", "vaibhav", "sachin"):
            cur.execute("UPDATE users SET team_leader_id = ?, team = 'Design Team' WHERE username = ?", (leader_id, eng))
    conn.commit()


def authenticate(username: str, password: str, db_path: str = DB_PATH) -> Optional[UserSession]:
    init_users_table(db_path)
    key = (username or "").strip().lower()
    if not key or not password:
        return None
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(_USER_SELECT + " WHERE LOWER(username) = ?", (key,))
    row = cur.fetchone()
    if not row or not row[5]:
        conn.close()
        return None
    cur.execute("SELECT salt, password_hash FROM users WHERE user_id = ?", (row[0],))
    cred = cur.fetchone()
    if not cred or not verify_password(password, cred[0], cred[1]):
        conn.close()
        return None
    now = datetime.now().isoformat()
    cur.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now, row[0]))
    conn.commit()
    conn.close()
    return _row_to_session(row)


def list_users(db_path: str = DB_PATH, include_inactive: bool = False) -> List[UserRecord]:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    sql = _USER_SELECT
    if not include_inactive:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY username"
    cur.execute(sql)
    rows = [_row_to_record(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_user_by_id(user_id: int, db_path: str = DB_PATH) -> Optional[UserRecord]:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(_USER_SELECT + " WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return _row_to_record(row) if row else None


def get_user_by_username(username: str, db_path: str = DB_PATH) -> Optional[UserRecord]:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(_USER_SELECT + " WHERE LOWER(username) = ?", (username.strip().lower(),))
    row = cur.fetchone()
    conn.close()
    return _row_to_record(row) if row else None


def username_exists(username: str, exclude_user_id: int = 0, db_path: str = DB_PATH) -> bool:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        _USER_SELECT + " WHERE LOWER(username) = ? AND user_id != ?",
        (username.strip().lower(), exclude_user_id),
    )
    exists = cur.fetchone() is not None
    conn.close()
    return exists


def list_team_engineers(team_leader_id: int, db_path: str = DB_PATH) -> List[UserRecord]:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        _USER_SELECT + " WHERE team_leader_id = ? AND role = ? AND is_active = 1 ORDER BY full_name",
        (team_leader_id, ROLE_ENGINEER),
    )
    rows = [_row_to_record(r) for r in cur.fetchall()]
    conn.close()
    return rows


def create_user(
    username: str,
    password: str,
    full_name: str,
    role: str,
    email: str = "",
    employee_id: str = "",
    team: str = "",
    team_leader_id: int = 0,
    db_path: str = DB_PATH,
) -> int:
    init_users_table(db_path)
    salt_hex, pwd_hash = hash_password(password)
    now = datetime.now().isoformat()
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users
        (username, password_hash, salt, full_name, role, email, is_active, created_at,
         employee_id, team, team_leader_id)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?)
        """,
        (username.strip().lower(), pwd_hash, salt_hex, full_name, role, email, now, employee_id, team, team_leader_id),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(user_id)


def update_user(
    user_id: int,
    full_name: str,
    role: str,
    email: str = "",
    employee_id: str = "",
    team: str = "",
    team_leader_id: int = 0,
    is_active: bool = True,
    db_path: str = DB_PATH,
) -> None:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET full_name = ?, role = ?, email = ?, employee_id = ?, team = ?,
               team_leader_id = ?, is_active = ?
        WHERE user_id = ?
        """,
        (full_name, role, email, employee_id, team, team_leader_id, int(is_active), user_id),
    )
    conn.commit()
    conn.close()


def reset_user_password(user_id: int, new_password: str, db_path: str = DB_PATH) -> None:
    salt_hex, pwd_hash = hash_password(new_password)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE user_id = ?",
        (pwd_hash, salt_hex, user_id),
    )
    conn.commit()
    conn.close()


def deactivate_user(user_id: int, db_path: str = DB_PATH) -> None:
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def count_active_users(db_path: str = DB_PATH) -> int:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    count = int(cur.fetchone()[0])
    conn.close()
    return count
