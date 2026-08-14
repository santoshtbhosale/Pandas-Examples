"""Automatic and manual SQLite database backups."""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import List

from services.database import DB_PATH, log_audit_event

KEEP_DEFAULT = 10


def _backup_dir(db_path: str = DB_PATH) -> str:
    return os.path.join(os.path.dirname(db_path), "backups")


def backup_database(db_path: str = DB_PATH, *, reason: str = "auto") -> str:
    """Copy the database to a timestamped backup file. Returns backup path."""
    if not os.path.isfile(db_path):
        raise FileNotFoundError(f"Database not found: {db_path}")
    backup_dir = _backup_dir(db_path)
    os.makedirs(backup_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"water_demand_{stamp}.db")
    shutil.copy2(db_path, dest)
    prune_backups(KEEP_DEFAULT, db_path)
    try:
        log_audit_event("db_backup", details=f"{reason}: {os.path.basename(dest)}", db_path=db_path)
    except Exception:
        pass
    return dest


def list_backups(db_path: str = DB_PATH) -> List[str]:
    """Return backup file paths newest first."""
    backup_dir = _backup_dir(db_path)
    if not os.path.isdir(backup_dir):
        return []
    files = [
        os.path.join(backup_dir, name)
        for name in os.listdir(backup_dir)
        if name.endswith(".db")
    ]
    files.sort(key=os.path.getmtime, reverse=True)
    return files


def prune_backups(keep: int = KEEP_DEFAULT, db_path: str = DB_PATH) -> None:
    """Remove oldest backups beyond the keep limit."""
    backups = list_backups(db_path)
    for path in backups[keep:]:
        try:
            os.remove(path)
        except OSError:
            pass


def restore_database(backup_path: str, db_path: str = DB_PATH) -> None:
    """Replace the active database with a backup copy."""
    if not os.path.isfile(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    shutil.copy2(backup_path, db_path)
    try:
        log_audit_event("db_restore", details=os.path.basename(backup_path), db_path=db_path)
    except Exception:
        pass
