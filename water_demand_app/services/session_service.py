"""Session context, remember-me, and inactivity timeout settings."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from models.user import UserSession

DEFAULT_TIMEOUT_MINUTES = 30
WARNING_BEFORE_SECONDS = 120

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMEMBER_FILE = os.path.join(APP_DIR, ".remember_login.json")
SESSION_CONFIG_FILE = os.path.join(APP_DIR, ".session_config.json")


@dataclass
class SessionContext:
    user: UserSession
    login_at: str = ""
    last_activity_at: str = ""
    login_date: str = ""
    login_time: str = ""

    def touch(self) -> None:
        self.last_activity_at = datetime.now().isoformat()

    @classmethod
    def from_user(cls, user: UserSession) -> "SessionContext":
        now = datetime.now()
        return cls(
            user=user,
            login_at=now.isoformat(),
            last_activity_at=now.isoformat(),
            login_date=now.strftime("%Y-%m-%d"),
            login_time=now.strftime("%H:%M:%S"),
        )


def load_remembered_username() -> str:
    try:
        if os.path.exists(REMEMBER_FILE):
            with open(REMEMBER_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return str(data.get("username", "")).strip()
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return ""


def save_remembered_username(username: str) -> None:
    username = (username or "").strip()
    if not username:
        clear_remembered_username()
        return
    try:
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump({"username": username}, f)
    except OSError:
        pass


def clear_remembered_username() -> None:
    try:
        if os.path.exists(REMEMBER_FILE):
            os.remove(REMEMBER_FILE)
    except OSError:
        pass


def get_timeout_minutes() -> int:
    try:
        if os.path.exists(SESSION_CONFIG_FILE):
            with open(SESSION_CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
            return max(5, int(data.get("timeout_minutes", DEFAULT_TIMEOUT_MINUTES)))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        pass
    return DEFAULT_TIMEOUT_MINUTES
