"""User authentication — SQLite users table with PBKDF2 password hashing."""

from __future__ import annotations

import hashlib
import secrets
import sqlite3
from datetime import datetime
from typing import List, Optional

from models.user import ROLE_ADMIN, ROLE_ENGINEER, ROLE_VIEWER, UserSession
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
            last_login TEXT
        )
        """
    )
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        _seed_default_users(cur)
        conn.commit()
    conn.close()


def _seed_default_users(cur: sqlite3.Cursor) -> None:
    now = datetime.now().isoformat()
    defaults = [
        ("admin", "Admin@123", "System Administrator", ROLE_ADMIN, "admin@americanedge.com"),
        ("akash", "Akash@123", "Akash", ROLE_ENGINEER, "akash@americanedge.com"),
        ("vaibhav", "Vaibhav@123", "Vaibhav", ROLE_ENGINEER, "vaibhav@americanedge.com"),
        ("sachin", "Sachin@123", "Sachin", ROLE_ENGINEER, "sachin@americanedge.com"),
        ("omkar", "Omkar@123", "Omkar", ROLE_VIEWER, "omkar@americanedge.com"),
    ]
    for username, password, full_name, role, email in defaults:
        salt_hex, pwd_hash = hash_password(password)
        cur.execute(
            """
            INSERT INTO users
            (username, password_hash, salt, full_name, role, email, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (username, pwd_hash, salt_hex, full_name, role, email, now),
        )


def authenticate(username: str, password: str, db_path: str = DB_PATH) -> Optional[UserSession]:
    init_users_table(db_path)
    key = (username or "").strip().lower()
    if not key or not password:
        return None
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, username, password_hash, salt, full_name, role, email, is_active
        FROM users WHERE LOWER(username) = ?
        """,
        (key,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return None
    user_id, uname, pwd_hash, salt_hex, full_name, role, email, is_active = row
    if not is_active:
        conn.close()
        return None
    if not verify_password(password, salt_hex, pwd_hash):
        conn.close()
        return None
    now = datetime.now().isoformat()
    cur.execute("UPDATE users SET last_login = ? WHERE user_id = ?", (now, user_id))
    conn.commit()
    conn.close()
    return UserSession(user_id=user_id, username=uname, full_name=full_name, role=role, email=email or "")


def list_users(db_path: str = DB_PATH) -> List[UserSession]:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT user_id, username, full_name, role, email
        FROM users WHERE is_active = 1 ORDER BY username
        """
    )
    rows = [
        UserSession(user_id=r[0], username=r[1], full_name=r[2], role=r[3], email=r[4] or "")
        for r in cur.fetchall()
    ]
    conn.close()
    return rows


def count_active_users(db_path: str = DB_PATH) -> int:
    init_users_table(db_path)
    conn = _conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
    count = int(cur.fetchone()[0])
    conn.close()
    return count
