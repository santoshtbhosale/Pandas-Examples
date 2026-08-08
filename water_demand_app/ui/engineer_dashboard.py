"""Engineer dashboard — projects, quick actions, timer info."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.project_service import find_projects
from services.project_workflow_service import dashboard_stats
from services.session_service import SessionContext
from ui.dashboard_header import build_dashboard_header
from ui.gui_safe import safe_command
from ui.project_hub import ProjectHub


class EngineerDashboard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        user: UserSession,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_launch_water_demand: Callable[[], None],
        on_logout: Callable[[], None],
        session: Optional[SessionContext] = None,
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.session = session
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_launch_water_demand = on_launch_water_demand
        self.on_logout = on_logout
        self.project_hub: Optional[ProjectHub] = None
        self._status_filter = ""
        self._list_frame: Optional[ctk.CTkFrame] = None
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        header = build_dashboard_header(
            self, "ENGINEER DASHBOARD", self.user,
            safe_command(self._logout, parent=self), session=self.session,
        )
        header.grid(row=0, column=0, sticky="ew")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body, text="Engineer Workspace",
            font=("Arial", 22, "bold"), text_color=BRAND_NAVY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        self._quick_actions(body, row=1)
        self._stats_row(body, row=2)
        self._list_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._list_frame.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        self.project_hub = ProjectHub(
            body, user=self.user, on_new_project=self.on_new_project,
            on_open_project=self.on_open_project, enabled=True,
        )
        self.project_hub.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        self._refresh_list()

    def _quick_actions(self, parent, row: int) -> None:
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        actions = [
            ("+ New Project", "#27AE60", self.on_new_project),
            ("📂 My Projects", "#2980B9", lambda: self._set_filter("")),
            ("⏱ Active", BRAND_ORANGE, lambda: self._set_filter("in_progress")),
            ("✓ Completed", "#27AE60", lambda: self._set_filter("completed")),
            ("⚠ Delayed", "#C0392B", lambda: self._set_filter("delayed")),
            ("🔍 Search", "#7F8C8D", self._focus_search),
        ]
        for i, (text, color, cmd) in enumerate(actions):
            ctk.CTkButton(
                bar, text=text, fg_color=color, height=36,
                command=safe_command(cmd, parent=self),
            ).grid(row=0, column=i, padx=4, sticky="ew")
            bar.grid_columnconfigure(i, weight=1)

    def _stats_row(self, parent, row: int) -> None:
        stat_row = ctk.CTkFrame(parent, fg_color="transparent")
        stat_row.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        stats = dashboard_stats(self.user)
        for i, (label, key) in enumerate([
            ("My Projects", "total"), ("In Progress", "in_progress"),
            ("Completed", "completed"), ("Delayed", "delayed"),
            ("Pending Approval", "pending_approval"),
        ]):
            card = ctk.CTkFrame(stat_row, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            stat_row.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=label, font=("Arial", 10, "bold")).pack(padx=10, pady=(8, 0))
            val = ctk.CTkLabel(card, text=str(stats.get(key, 0)), font=("Arial", 20, "bold"), text_color=BRAND_ORANGE)
            val.pack(padx=10, pady=(0, 8))
            self._stat_labels[key] = val

    def _set_filter(self, status: str) -> None:
        self._status_filter = status
        self._refresh_list()

    def _refresh_list(self) -> None:
        if not self._list_frame:
            return
        for w in self._list_frame.winfo_children():
            w.destroy()
        stats = dashboard_stats(self.user)
        for key, lbl in self._stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

        assigned = find_projects(user=self.user, status_filter=self._status_filter)
        info = ctk.CTkFrame(self._list_frame, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
        info.pack(fill="x")
        title = "Project History" if not self._status_filter else f"Filtered — {self._status_filter.replace('_', ' ').title()}"
        ctk.CTkLabel(info, text=title, font=("Arial", 13, "bold"), text_color=BRAND_NAVY).pack(anchor="w", padx=12, pady=(10, 4))
        if not assigned:
            ctk.CTkLabel(info, text="No projects found.", font=("Arial", 10), text_color="#888888").pack(anchor="w", padx=12, pady=8)
        else:
            for p in assigned[:10]:
                line = (
                    f"{p['project_id']}  |  {(p['project_name'] or '')[:28]}  |  "
                    f"{p.get('project_type', '')}  |  Status: {p.get('status', 'n/a')}  |  "
                    f"Elapsed: {p.get('elapsed_display', '-')}  |  Remaining: {p.get('remaining_display', '-')}"
                )
                ctk.CTkLabel(info, text=line, font=("Arial", 10), anchor="w").pack(anchor="w", padx=12, pady=2)
        ctk.CTkLabel(info, text="").pack(pady=4)

    def _focus_search(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Are you sure you want to logout?", parent=self.winfo_toplevel()):
            self.on_logout()

    def refresh_stats(self) -> None:
        self._refresh_list()
        if self.project_hub:
            self.project_hub.refresh()
