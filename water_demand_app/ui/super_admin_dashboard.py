"""Super Admin dashboard — user management, audit logs, system stats."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox, simpledialog

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import ROLE_LABELS, USER_ROLES, UserSession
from services.audit_service import list_audit_logs
from services.auth_db import (
    count_active_users,
    create_user,
    deactivate_user,
    list_users,
    reset_user_password,
)
from services.project_workflow_service import dashboard_stats


class SuperAdminDashboard(ctk.CTkFrame):
    def __init__(self, master, user: UserSession, on_logout: Callable[[], None]) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.on_logout = on_logout
        self._user_list: Optional[ctk.CTkScrollableFrame] = None
        self._audit_list: Optional[ctk.CTkScrollableFrame] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        top = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        ctk.CTkLabel(top, text="SUPER ADMIN", font=("Arial", 16, "bold"), text_color=BRAND_ORANGE).grid(row=0, column=0, padx=24, pady=20, sticky="w")
        ctk.CTkButton(top, text="Logout", command=self._logout, fg_color="#C0392B", width=90).grid(row=0, column=1, padx=24, sticky="e")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        body.grid_columnconfigure(0, weight=1)

        stats = dashboard_stats()
        ctk.CTkLabel(body, text="System Overview", font=("Arial", 20, "bold"), text_color=BRAND_NAVY).grid(row=0, column=0, sticky="w", pady=(0, 8))
        ctk.CTkLabel(
            body,
            text=f"Projects: {stats['total']}  |  Users: {count_active_users()}  |  In Progress: {stats['in_progress']}  |  Completed: {stats['completed']}",
            font=("Arial", 12),
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkButton(actions, text="+ Create User", fg_color="#27AE60", command=self._create_user).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Refresh", command=self.refresh).pack(side="left", padx=4)

        self._user_list = ctk.CTkScrollableFrame(body, height=200, label_text="Users")
        self._user_list.grid(row=3, column=0, sticky="ew", pady=8)
        self._audit_list = ctk.CTkScrollableFrame(body, height=200, label_text="Audit Log")
        self._audit_list.grid(row=4, column=0, sticky="ew", pady=8)
        self.refresh()

    def refresh(self) -> None:
        if self._user_list:
            for w in self._user_list.winfo_children():
                w.destroy()
            for u in list_users(include_inactive=True):
                row = ctk.CTkFrame(self._user_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                status = "Active" if u.is_active else "Inactive"
                ctk.CTkLabel(
                    row,
                    text=f"{u.username} | {u.full_name} | {ROLE_LABELS.get(u.role, u.role)} | {u.team} | {status}",
                    font=("Arial", 10), anchor="w",
                ).pack(side="left", padx=4)
                if u.is_active and u.user_id != self.user.user_id:
                    ctk.CTkButton(row, text="Reset Pwd", width=70, height=24, command=lambda uid=u.user_id: self._reset_pwd(uid)).pack(side="right", padx=2)
                    ctk.CTkButton(row, text="Deactivate", width=80, height=24, fg_color="#C0392B", command=lambda uid=u.user_id: self._deactivate(uid)).pack(side="right", padx=2)
        if self._audit_list:
            for w in self._audit_list.winfo_children():
                w.destroy()
            for entry in list_audit_logs(limit=50):
                ts = (entry.get("timestamp") or "")[:19].replace("T", " ")
                line = f"{ts} | {entry.get('username', '')} | {entry.get('action', '')} | {entry.get('project_id', '')} | {entry.get('field_name', '')} {entry.get('old_value', '')} → {entry.get('new_value', '')}"
                ctk.CTkLabel(self._audit_list, text=line[:120], font=("Arial", 9), anchor="w").pack(anchor="w", padx=4, pady=1)

    def _create_user(self) -> None:
        username = simpledialog.askstring("Create User", "Username:", parent=self)
        if not username:
            return
        password = simpledialog.askstring("Create User", "Password:", parent=self, show="*")
        if not password:
            return
        full_name = simpledialog.askstring("Create User", "Full Name:", parent=self) or username
        role = simpledialog.askstring("Create User", f"Role ({', '.join(USER_ROLES)}):", parent=self) or "engineer"
        emp_id = simpledialog.askstring("Create User", "Employee ID:", parent=self) or ""
        team = simpledialog.askstring("Create User", "Team:", parent=self) or ""
        tl_id = 0
        if role == "engineer":
            leaders = [u for u in list_users() if u.role == "team_leader"]
            if leaders:
                tl_id = leaders[0].user_id
        try:
            create_user(username, password, full_name, role, employee_id=emp_id, team=team, team_leader_id=tl_id)
            from services.audit_service import ACTION_USER_CREATED, log_audit
            log_audit(ACTION_USER_CREATED, self.user.username, self.user.user_id, reason=f"Created {username}")
            messagebox.showinfo("Created", f"User {username} created.")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def _reset_pwd(self, user_id: int) -> None:
        pwd = simpledialog.askstring("Reset Password", "New password:", parent=self, show="*")
        if pwd:
            reset_user_password(user_id, pwd)
            messagebox.showinfo("Done", "Password reset.")

    def _deactivate(self, user_id: int) -> None:
        if messagebox.askyesno("Deactivate", "Deactivate this user?"):
            deactivate_user(user_id)
            from services.audit_service import ACTION_USER_DEACTIVATED, log_audit
            log_audit(ACTION_USER_DEACTIVATED, self.user.username, self.user.user_id, reason=str(user_id))
            self.refresh()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Logout?"):
            self.on_logout()

    def refresh_stats(self) -> None:
        self.refresh()
