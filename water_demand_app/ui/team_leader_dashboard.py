"""Team Leader dashboard — live monitor, team projects, performance."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE, PROJECT_TYPE_LABELS
from models.user import UserSession
from services.auth_db import list_team_engineers
from services.project_service import create_new_project_state, find_projects, persist_project_state
from services.project_workflow_service import assign_project, dashboard_stats, engineer_performance
from services.session_service import SessionContext
from ui.dashboard_header import build_dashboard_header
from ui.gui_safe import safe_command
from ui.project_assign_dialog import ProjectAssignDialog

STATUS_COLORS = {
    "in_progress": "#27AE60",
    "delayed": "#C0392B",
    "completed": "#2980B9",
    "not_started": "#F39C12",
    "paused": "#F39C12",
    "pending_approval": "#8E44AD",
}


class TeamLeaderDashboard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        user: UserSession,
        on_open_project: Callable[[str], None],
        on_logout: Callable[[], None],
        on_assign_and_open: Callable[[str], None],
        session: Optional[SessionContext] = None,
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.session = session
        self.on_open_project = on_open_project
        self.on_logout = on_logout
        self.on_assign_and_open = on_assign_and_open
        self._status_filter = ""
        self._date_filter = ""
        self._search_var = ctk.StringVar()
        self._table_frame: Optional[ctk.CTkScrollableFrame] = None
        self._live_frame: Optional[ctk.CTkFrame] = None
        self._perf_frame: Optional[ctk.CTkFrame] = None
        self._refresh_job: Optional[str] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = build_dashboard_header(
            self, "TEAM LEADER DASHBOARD", self.user,
            safe_command(self._logout, parent=self), session=self.session,
        )
        header.grid(row=0, column=0, sticky="ew")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(body, text="Team Leader Workspace", font=("Arial", 22, "bold"), text_color=BRAND_NAVY).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self._stats_row(body)
        self._live_monitor(body)
        self._toolbar(body)
        self._table_frame = ctk.CTkScrollableFrame(body, height=220, label_text="Team Projects")
        self._table_frame.grid(row=4, column=0, sticky="ew", pady=8)
        self._perf_frame = ctk.CTkFrame(body, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        self._perf_frame.grid(row=5, column=0, sticky="ew", pady=8)
        self.refresh()
        self._schedule_refresh()

    def _schedule_refresh(self) -> None:
        if self._refresh_job is not None:
            self.after_cancel(self._refresh_job)
        self._refresh_job = self.after(30_000, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self.refresh()
        self._schedule_refresh()

    def destroy(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
        super().destroy()

    def _stats_row(self, parent) -> None:
        stats = dashboard_stats(self.user)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        labels = [
            ("Total Projects", "total"), ("Today's Projects", "today"), ("In Progress", "in_progress"),
            ("Completed", "completed"), ("Delayed", "delayed"), ("Pending Approval", "pending_approval"),
        ]
        for i, (title, key) in enumerate(labels):
            card = ctk.CTkFrame(row, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
            card.grid(row=0, column=i, padx=2, sticky="nsew")
            row.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=title, font=("Arial", 9, "bold")).pack(padx=6, pady=(6, 0))
            ctk.CTkLabel(card, text=str(stats.get(key, 0)), font=("Arial", 16, "bold"), text_color=BRAND_ORANGE).pack(padx=6, pady=(0, 6))

    def _live_monitor(self, parent) -> None:
        self._live_frame = ctk.CTkFrame(parent, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        self._live_frame.grid(row=2, column=0, sticky="ew", pady=8)

    def _render_live_monitor(self, projects: list) -> None:
        if not self._live_frame:
            return
        for w in self._live_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._live_frame, text="LIVE PROJECT MONITOR", font=("Arial", 13, "bold"), text_color=BRAND_NAVY,
        ).pack(anchor="w", padx=12, pady=(10, 6))
        hdr = ctk.CTkFrame(self._live_frame, fg_color="#E8ECF0")
        hdr.pack(fill="x", padx=12, pady=(0, 4))
        for i, h in enumerate(["Project", "Engineer", "Type", "Status", "Elapsed", "Remaining"]):
            ctk.CTkLabel(hdr, text=h, font=("Arial", 9, "bold"), width=110, anchor="w").grid(row=0, column=i, padx=4, pady=4)
        active = [p for p in projects if p.get("status") in ("in_progress", "delayed", "paused")][:8]
        if not active:
            ctk.CTkLabel(self._live_frame, text="No active team projects.", font=("Arial", 10), text_color="#888888").pack(anchor="w", padx=12, pady=8)
            return
        for p in active:
            status = p.get("status", "")
            color = STATUS_COLORS.get(status, "#333333")
            row = ctk.CTkFrame(self._live_frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)
            vals = [
                (p["project_id"] or "")[:12],
                (p.get("engineer_name") or p.get("assigned_to_username") or "")[:12],
                (p.get("project_type") or "")[:12],
                status.replace("_", " ").title(),
                p.get("elapsed_display", "-"),
                p.get("remaining_display", "-"),
            ]
            for i, v in enumerate(vals):
                fg = color if i == 3 else "#333333"
                ctk.CTkLabel(row, text=v, font=("Arial", 9), width=110, anchor="w", text_color=fg).grid(row=0, column=i, padx=4)

    def _toolbar(self, parent) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", pady=4)
        ctk.CTkEntry(bar, textvariable=self._search_var, placeholder_text="Search by ID, name, client, engineer...", width=260).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bar, text="Search", width=70, command=self.refresh).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="+ Assign Project", fg_color="#27AE60", command=safe_command(self._assign_new, parent=self)).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="In Progress", width=90, command=lambda: self._set_status("in_progress")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Delayed", width=70, command=lambda: self._set_status("delayed")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Clear", width=60, command=self._clear_filters).pack(side="left", padx=2)

    def _set_date_filter(self, kind: str) -> None:
        today = datetime.now().date()
        if kind == "today":
            self._date_filter = today.isoformat()
        elif kind == "7d":
            self._date_filter = (today - timedelta(days=7)).isoformat()
        self.refresh()

    def _set_status(self, status: str) -> None:
        self._status_filter = status
        self.refresh()

    def _clear_filters(self) -> None:
        self._status_filter = ""
        self._date_filter = ""
        self._search_var.set("")
        self.refresh()

    def refresh(self) -> None:
        if not self._table_frame:
            return
        date_from = self._date_filter if self._date_filter else ""
        projects = find_projects(
            query=self._search_var.get(),
            limit=100,
            user=self.user,
            status_filter=self._status_filter,
            date_from=date_from,
        )
        self._render_live_monitor(projects)
        for w in self._table_frame.winfo_children():
            w.destroy()
        headers = ["ID", "Name", "Type", "Engineer", "Status", "Elapsed", "Remaining", "Progress", "Actions"]
        hdr = ctk.CTkFrame(self._table_frame, fg_color="#E8ECF0")
        hdr.pack(fill="x", pady=(0, 4))
        for i, h in enumerate(headers):
            ctk.CTkLabel(hdr, text=h, font=("Arial", 9, "bold"), width=90 if i < 7 else 70).grid(row=0, column=i, padx=2, pady=4)
        for p in projects:
            row = ctk.CTkFrame(self._table_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            status = p.get("status", "")
            color = STATUS_COLORS.get(status, "#333333")
            vals = [
                p["project_id"][:12],
                (p["project_name"] or "")[:16],
                (p.get("project_type") or "")[:12],
                (p.get("engineer_name") or "")[:12],
                status,
                p.get("elapsed_display", "-"),
                p.get("remaining_display", "-"),
                f"{p.get('progress_pct', 0)}%",
            ]
            for i, v in enumerate(vals):
                ctk.CTkLabel(row, text=v, font=("Arial", 9), width=90 if i < 7 else 70, anchor="w", text_color=color if i == 4 else "#333333").grid(row=0, column=i, padx=2)
            pid = p["project_id"]
            ctk.CTkButton(row, text="Open", width=50, height=24, command=lambda x=pid: self.on_open_project(x)).grid(row=0, column=8, padx=2)
        self._refresh_performance()

    def _refresh_performance(self) -> None:
        if not self._perf_frame:
            return
        for w in self._perf_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._perf_frame, text="Engineer Performance", font=("Arial", 13, "bold"), text_color=BRAND_NAVY).pack(anchor="w", padx=12, pady=(10, 4))
        perf = engineer_performance(self.user.user_id)
        if not perf:
            ctk.CTkLabel(self._perf_frame, text="No engineers in your team.", font=("Arial", 10)).pack(anchor="w", padx=12, pady=8)
            return
        for row in perf:
            text = (
                f"{row['engineer_name']}: Created {row['assigned']} | Completed {row['completed']} | "
                f"In Progress {row['in_progress']} | Delayed {row['delayed']} | "
                f"Early {row['early']} | On Time {row['on_time']} | Late {row['late']}"
            )
            ctk.CTkLabel(self._perf_frame, text=text, font=("Arial", 10), anchor="w").pack(anchor="w", padx=12, pady=2)
        ctk.CTkLabel(self._perf_frame, text="").pack(pady=4)

    def _assign_new(self) -> None:
        engineers = list_team_engineers(self.user.user_id)
        if not engineers:
            messagebox.showwarning("No Engineers", "No engineers assigned to your team.", parent=self.winfo_toplevel())
            return
        dlg = ProjectAssignDialog(self.winfo_toplevel(), engineers, list(PROJECT_TYPE_LABELS.keys()))
        self.wait_window(dlg)
        if not dlg.result:
            return
        state = create_new_project_state(self.user)
        state.project.project_name = dlg.result["project_name"]
        state.project.client_name = dlg.result["client_name"]
        state.project.project_type = dlg.result["project_type"]
        persist_project_state(state, self.user)
        assign_project(
            state.project.project_id,
            dlg.result["engineer_username"],
            self.user,
            duration_label=dlg.result["duration"],
            custom_minutes=int(dlg.result.get("custom_minutes") or 0),
            priority=dlg.result.get("priority", "Normal"),
        )
        messagebox.showinfo("Assigned", f"Project {state.project.project_id} assigned.", parent=self.winfo_toplevel())
        self.refresh()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Logout?", parent=self.winfo_toplevel()):
            self.on_logout()

    def refresh_stats(self) -> None:
        self.refresh()
