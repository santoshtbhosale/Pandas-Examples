"""Engineer dashboard — assigned projects, timer info, project hub."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.project_service import find_projects
from services.project_workflow_service import dashboard_stats
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
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.user = user
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_launch_water_demand = on_launch_water_demand
        self.on_logout = on_logout
        self.project_hub: Optional[ProjectHub] = None
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self._header()
        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body, text=f"Engineer Dashboard — {self.user.full_name}",
            font=("Arial", 22, "bold"), text_color=BRAND_NAVY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))

        stats = dashboard_stats(self.user)
        stat_row = ctk.CTkFrame(body, fg_color="transparent")
        stat_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        for i, (label, key) in enumerate([
            ("My Projects", "total"), ("In Progress", "in_progress"),
            ("Completed", "completed"), ("Delayed", "delayed"),
        ]):
            card = ctk.CTkFrame(stat_row, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
            card.grid(row=0, column=i, padx=4, sticky="nsew")
            stat_row.grid_columnconfigure(i, weight=1)
            ctk.CTkLabel(card, text=label, font=("Arial", 10, "bold")).pack(padx=10, pady=(8, 0))
            ctk.CTkLabel(card, text=str(stats.get(key, 0)), font=("Arial", 20, "bold"), text_color=BRAND_ORANGE).pack(padx=10, pady=(0, 8))

        assigned = find_projects(user=self.user)
        if assigned:
            info = ctk.CTkFrame(body, fg_color="white", corner_radius=8, border_width=1, border_color="#DDDDDD")
            info.grid(row=2, column=0, sticky="ew", pady=(0, 12))
            ctk.CTkLabel(info, text="Assigned Projects", font=("Arial", 13, "bold"), text_color=BRAND_NAVY).pack(anchor="w", padx=12, pady=(10, 4))
            for p in assigned[:8]:
                line = (
                    f"{p['project_id']}  |  {p['project_name'][:30]}  |  "
                    f"Status: {p.get('status', 'n/a')}  |  "
                    f"Elapsed: {p.get('elapsed_display', '-')}  |  "
                    f"Remaining: {p.get('remaining_display', '-')}"
                )
                ctk.CTkLabel(info, text=line, font=("Arial", 10), anchor="w").pack(anchor="w", padx=12, pady=2)
            ctk.CTkLabel(info, text="").pack(pady=4)

        self.project_hub = ProjectHub(
            body, user=self.user, on_new_project=self.on_new_project,
            on_open_project=self.on_open_project, enabled=True,
        )
        self.project_hub.grid(row=3, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            body, text="Launch Calculator (Blank)", fg_color=BRAND_ORANGE,
            command=self._launch, height=36,
        ).grid(row=4, column=0, sticky="w")

    def _header(self) -> None:
        top = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(top, text="AMERICAN EDGE ENGINEERS", font=("Arial", 16, "bold"), text_color=BRAND_ORANGE).grid(row=0, column=0, padx=24, pady=20, sticky="w")
        uf = ctk.CTkFrame(top, fg_color="transparent")
        uf.grid(row=0, column=1, sticky="e", padx=16)
        ctk.CTkLabel(uf, text=f"{self.user.full_name} • Engineer", font=("Arial", 12), text_color="white").pack(side="left", padx=(0, 12))
        ctk.CTkButton(uf, text="Logout", command=self._logout, fg_color="#C0392B", width=90).pack(side="left")

    def _launch(self) -> None:
        self.on_launch_water_demand()

    def _logout(self) -> None:
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.on_logout()

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()
