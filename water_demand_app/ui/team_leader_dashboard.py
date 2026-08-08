"""Team Leader dashboard — team projects, assignment, performance."""

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
from ui.project_assign_dialog import ProjectAssignDialog


class TeamLeaderDashboard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        user: UserSession,
        on_open_project: Callable[[str], None],
        on_logout: Callable[[], None],
        on_assign_and_open: Callable[[str], None],
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.on_open_project = on_open_project
        self.on_logout = on_logout
        self.on_assign_and_open = on_assign_and_open
        self._status_filter = ""
        self._date_filter = ""
        self._search_var = ctk.StringVar()
        self._table_frame: Optional[ctk.CTkScrollableFrame] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._header()
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=12)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(body, text="Team Leader Dashboard", font=("Arial", 22, "bold"), text_color=BRAND_NAVY).grid(row=0, column=0, sticky="w", pady=(0, 10))
        self._stats_row(body)
        self._toolbar(body)
        self._table_frame = ctk.CTkScrollableFrame(body, height=260, label_text="Team Projects")
        self._table_frame.grid(row=3, column=0, sticky="ew", pady=8)
        self._perf_frame = ctk.CTkFrame(body, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        self._perf_frame.grid(row=4, column=0, sticky="ew", pady=8)
        self.refresh()

    def _header(self) -> None:
        top = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="TEAM LEADER", font=("Arial", 16, "bold"), text_color=BRAND_ORANGE).grid(row=0, column=0, padx=24, pady=20, sticky="w")
        uf = ctk.CTkFrame(top, fg_color="transparent")
        uf.grid(row=0, column=1, sticky="e", padx=16)
        ctk.CTkLabel(uf, text=f"{self.user.full_name}", font=("Arial", 12), text_color="white").pack(side="left", padx=(0, 12))
        ctk.CTkButton(uf, text="Logout", command=self._logout, fg_color="#C0392B", width=90).pack(side="left")

    def _stats_row(self, parent) -> None:
        stats = dashboard_stats(self.user)
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        labels = [
            ("Total", "total"), ("Today", "today"), ("In Progress", "in_progress"),
            ("Completed", "completed"), ("Pending", "pending"), ("Delayed", "delayed"),
            ("Pending Approval", "pending_approval"),
        ]
        for i, (title, key) in enumerate(labels):
            card = ctk.CTkFrame(row, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
            card.grid(row=0, column=i, padx=2, sticky="nsew")
            row.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=title, font=("Arial", 9, "bold")).pack(padx=6, pady=(6, 0))
            ctk.CTkLabel(card, text=str(stats.get(key, 0)), font=("Arial", 16, "bold"), text_color=BRAND_ORANGE).pack(padx=6, pady=(0, 6))

    def _toolbar(self, parent) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=2, column=0, sticky="ew", pady=4)
        ctk.CTkEntry(bar, textvariable=self._search_var, placeholder_text="Search...", width=220).pack(side="left", padx=(0, 6))
        ctk.CTkButton(bar, text="Search", width=70, command=self.refresh).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="+ Assign Project", fg_color="#27AE60", command=self._assign_new).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Today", width=60, command=lambda: self._set_date_filter("today")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Last 7 Days", width=90, command=lambda: self._set_date_filter("7d")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="In Progress", width=90, command=lambda: self._set_status("in_progress")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Delayed", width=70, command=lambda: self._set_status("delayed")).pack(side="left", padx=2)
        ctk.CTkButton(bar, text="Clear Filters", width=90, command=self._clear_filters).pack(side="left", padx=2)

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
        for w in self._table_frame.winfo_children():
            w.destroy()
        date_from = self._date_filter if self._date_filter else ""
        projects = find_projects(
            query=self._search_var.get(),
            limit=100,
            user=self.user,
            status_filter=self._status_filter,
            date_from=date_from,
        )
        headers = ["ID", "Name", "Engineer", "Status", "Elapsed", "Remaining", "Actions"]
        hdr = ctk.CTkFrame(self._table_frame, fg_color="#E8ECF0")
        hdr.pack(fill="x", pady=(0, 4))
        for i, h in enumerate(headers):
            ctk.CTkLabel(hdr, text=h, font=("Arial", 9, "bold"), width=100 if i < 5 else 80).grid(row=0, column=i, padx=2, pady=4)
        for p in projects:
            row = ctk.CTkFrame(self._table_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            vals = [
                p["project_id"][:14],
                (p["project_name"] or "")[:18],
                (p["engineer_name"] or "")[:12],
                p.get("status", ""),
                p.get("elapsed_display", "-"),
                p.get("remaining_display", "-"),
            ]
            for i, v in enumerate(vals):
                ctk.CTkLabel(row, text=v, font=("Arial", 9), width=100 if i < 5 else 80, anchor="w").grid(row=0, column=i, padx=2)
            pid = p["project_id"]
            ctk.CTkButton(row, text="Open", width=50, height=24, command=lambda x=pid: self.on_open_project(x)).grid(row=0, column=6, padx=2)
        self._refresh_performance()

    def _refresh_performance(self) -> None:
        for w in self._perf_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(self._perf_frame, text="Engineer Performance", font=("Arial", 13, "bold"), text_color=BRAND_NAVY).pack(anchor="w", padx=12, pady=(10, 4))
        perf = engineer_performance(self.user.user_id)
        if not perf:
            ctk.CTkLabel(self._perf_frame, text="No engineers in your team.", font=("Arial", 10)).pack(anchor="w", padx=12, pady=8)
            return
        for row in perf:
            text = (
                f"{row['engineer_name']}: Assigned {row['assigned']} | Completed {row['completed']} | "
                f"In Progress {row['in_progress']} | Delayed {row['delayed']} | "
                f"Early {row['early']} | On Time {row['on_time']} | Late {row['late']}"
            )
            ctk.CTkLabel(self._perf_frame, text=text, font=("Arial", 10), anchor="w").pack(anchor="w", padx=12, pady=2)
        ctk.CTkLabel(self._perf_frame, text="").pack(pady=4)

    def _assign_new(self) -> None:
        engineers = list_team_engineers(self.user.user_id)
        if not engineers:
            messagebox.showwarning("No Engineers", "No engineers assigned to your team.")
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
        messagebox.showinfo("Assigned", f"Project {state.project.project_id} assigned.")
        self.refresh()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Logout?"):
            self.on_logout()

    def refresh_stats(self) -> None:
        self.refresh()
