"""Super Admin dashboard — user management, audit logs, system stats."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import ROLE_LABELS, UserSession
from services.audit_service import list_audit_logs
from services.auth_db import (
    count_active_users,
    deactivate_user,
    list_users,
)
from services.project_workflow_service import dashboard_stats
from ui.create_user_dialog import CreateUserDialog, ResetPasswordDialog, ViewUserDialog
from services.session_service import SessionContext
from ui.dashboard_header import build_dashboard_header
from ui.gui_safe import safe_command


class SuperAdminDashboard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        user: UserSession,
        on_logout: Callable[[], None],
        session=None,
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.session = session
        self.on_logout = on_logout
        self._user_list: Optional[ctk.CTkScrollableFrame] = None
        self._audit_list: Optional[ctk.CTkScrollableFrame] = None
        self._search_var = ctk.StringVar()
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = build_dashboard_header(
            self, "SUPER ADMIN", self.user,
            safe_command(self._logout, parent=self), session=self.session,
        )
        header.grid(row=0, column=0, sticky="ew")

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
        ctk.CTkButton(
            actions, text="+ Create User", fg_color="#27AE60",
            command=safe_command(self._create_user, parent=self),
        ).pack(side="left", padx=4)
        ctk.CTkButton(actions, text="Refresh", command=safe_command(self.refresh, parent=self)).pack(side="left", padx=4)

        search_row = ctk.CTkFrame(body, fg_color="transparent")
        search_row.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkLabel(search_row, text="Search User:", font=("Arial", 11)).pack(side="left", padx=(0, 8))
        search_entry = ctk.CTkEntry(search_row, textvariable=self._search_var, width=260, placeholder_text="Name, username, role, team...")
        search_entry.pack(side="left", padx=(0, 8))
        self._search_var.trace_add("write", lambda *_: self.refresh())
        ctk.CTkButton(search_row, text="Clear", width=70, command=self._clear_search).pack(side="left")

        self._user_list = ctk.CTkScrollableFrame(body, height=200, label_text="Users")
        self._user_list.grid(row=4, column=0, sticky="ew", pady=8)
        self._audit_list = ctk.CTkScrollableFrame(body, height=200, label_text="Audit Log")
        self._audit_list.grid(row=5, column=0, sticky="ew", pady=8)
        self.refresh()

    def _clear_search(self) -> None:
        self._search_var.set("")

    def _matches_search(self, user, query: str) -> bool:
        if not query:
            return True
        q = query.lower()
        haystack = " ".join([
            user.username, user.full_name, user.employee_id, user.team,
            ROLE_LABELS.get(user.role, user.role),
        ]).lower()
        return q in haystack

    def refresh(self) -> None:
        query = self._search_var.get().strip() if hasattr(self, "_search_var") else ""
        if self._user_list:
            for w in self._user_list.winfo_children():
                w.destroy()
            for u in list_users(include_inactive=True):
                if not self._matches_search(u, query):
                    continue
                row = ctk.CTkFrame(self._user_list, fg_color="transparent")
                row.pack(fill="x", pady=2)
                status = "Active" if u.is_active else "Inactive"
                ctk.CTkLabel(
                    row,
                    text=f"{u.username} | {u.full_name} | {ROLE_LABELS.get(u.role, u.role)} | {u.team} | {status}",
                    font=("Arial", 10), anchor="w",
                ).pack(side="left", padx=4)
                ctk.CTkButton(row, text="View", width=56, height=24, command=lambda user=u: self._view_user(user)).pack(side="right", padx=2)
                ctk.CTkButton(row, text="Edit", width=56, height=24, command=lambda user=u: self._edit_user(user)).pack(side="right", padx=2)
                if u.is_active and u.user_id != self.user.user_id:
                    ctk.CTkButton(row, text="Reset Pwd", width=70, height=24, command=lambda user=u: self._reset_pwd(user)).pack(side="right", padx=2)
                    ctk.CTkButton(row, text="Deactivate", width=80, height=24, fg_color="#C0392B", command=lambda uid=u.user_id: self._deactivate(uid)).pack(side="right", padx=2)
        if self._audit_list:
            for w in self._audit_list.winfo_children():
                w.destroy()
            for entry in list_audit_logs(limit=50):
                ts = (entry.get("timestamp") or "")[:19].replace("T", " ")
                line = f"{ts} | {entry.get('username', '')} | {entry.get('action', '')} | {entry.get('project_id', '')} | {entry.get('field_name', '')} {entry.get('old_value', '')} → {entry.get('new_value', '')}"
                ctk.CTkLabel(self._audit_list, text=line[:120], font=("Arial", 9), anchor="w").pack(anchor="w", padx=4, pady=1)

    def _create_user(self) -> None:
        CreateUserDialog(self.winfo_toplevel(), actor_username=self.user.username, on_saved=self.refresh)

    def _edit_user(self, user) -> None:
        CreateUserDialog(
            self.winfo_toplevel(),
            actor_username=self.user.username,
            on_saved=self.refresh,
            edit_user=user,
        )

    def _view_user(self, user) -> None:
        ViewUserDialog(self.winfo_toplevel(), user)

    def _reset_pwd(self, user) -> None:
        ResetPasswordDialog(self.winfo_toplevel(), user, on_saved=self.refresh)

    def _deactivate(self, user_id: int) -> None:
        if messagebox.askyesno("Deactivate", "Deactivate this user?", parent=self.winfo_toplevel()):
            deactivate_user(user_id)
            from services.audit_service import ACTION_USER_DEACTIVATED, log_audit
            log_audit(ACTION_USER_DEACTIVATED, self.user.username, self.user.user_id, reason=str(user_id))
            self.refresh()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Logout?", parent=self.winfo_toplevel()):
            self.on_logout()

    def refresh_stats(self) -> None:
        self.refresh()
