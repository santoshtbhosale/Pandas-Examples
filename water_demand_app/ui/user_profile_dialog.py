"""User profile dialog — read-only account details."""

from __future__ import annotations

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import ROLE_LABELS, UserSession
from services.auth_db import get_user_by_id, list_users
from services.session_service import SessionContext


class UserProfileDialog(ctk.CTkToplevel):
    def __init__(self, master, user: UserSession, session: SessionContext | None = None) -> None:
        super().__init__(master)
        self.title("User Profile")
        self.geometry("420x400")
        self.transient(master.winfo_toplevel())
        self.grab_set()

        record = get_user_by_id(user.user_id)
        leader_name = "—"
        if user.team_leader_id:
            leader = next((u for u in list_users(include_inactive=True) if u.user_id == user.team_leader_id), None)
            if leader:
                leader_name = f"{leader.full_name} ({leader.username})"

        last_login = (record.created_at or "")[:19].replace("T", " ") if record else "—"
        if record and hasattr(record, "created_at"):
            pass
        from services.auth_db import _USER_SELECT, _conn
        from services.database import DB_PATH

        conn = _conn(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT last_login FROM users WHERE user_id = ?", (user.user_id,))
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            last_login = row[0][:19].replace("T", " ")

        ctk.CTkLabel(self, text="Profile", font=("Arial", 16, "bold"), text_color=BRAND_NAVY).pack(pady=12)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=8)

        rows = [
            ("Name", user.full_name),
            ("Username", user.username),
            ("Employee ID", user.employee_id or "—"),
            ("Role", ROLE_LABELS.get(user.role, user.role)),
            ("Team", user.team or "—"),
            ("Team Leader", leader_name),
            ("Last Login", last_login),
        ]
        if session:
            rows.extend([
                ("Login Date", session.login_date),
                ("Login Time", session.login_time),
            ])

        for i, (label, value) in enumerate(rows):
            ctk.CTkLabel(frame, text=label, font=("Arial", 11, "bold"), anchor="w").grid(row=i, column=0, sticky="w", pady=4)
            ctk.CTkLabel(frame, text=value, font=("Arial", 11), anchor="w").grid(row=i, column=1, sticky="w", padx=(12, 0), pady=4)

        ctk.CTkLabel(
            self,
            text="Role changes must be made by a Super Admin.",
            font=("Arial", 10, "italic"),
            text_color="#888888",
        ).pack(pady=(4, 8))
        ctk.CTkButton(self, text="Close", fg_color=BRAND_ORANGE, command=self.destroy).pack(pady=12)
