from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from models.user import UserSession
from services.auth_db import count_active_users
from services.project_service import find_projects
from ui.project_hub import ProjectHub


class DashboardScreen(ctk.CTkFrame):
    """Post-login dashboard with project management and module launcher."""

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

        top = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=72)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            top,
            text="AMERICAN EDGE ENGINEERS",
            font=("Arial", 16, "bold"),
            text_color=BRAND_ORANGE,
        ).grid(row=0, column=0, padx=24, pady=20, sticky="w")

        user_frame = ctk.CTkFrame(top, fg_color="transparent")
        user_frame.grid(row=0, column=1, padx=16, sticky="e")
        ctk.CTkLabel(
            user_frame,
            text=f"{self.user.full_name}  •  {self.user.role_label}",
            font=("Arial", 12),
            text_color="white",
        ).pack(side="left", padx=(0, 12))
        ctk.CTkButton(
            user_frame,
            text="Logout",
            command=self._confirm_logout,
            fg_color="#C0392B",
            hover_color="#A93226",
            width=90,
            height=32,
        ).pack(side="left")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text=f"Welcome, {self.user.full_name}",
            font=("Arial", 24, "bold"),
            text_color=BRAND_NAVY,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Manage projects or launch the Water Demand calculator.",
            font=("Arial", 13),
            text_color="#666666",
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        stats = ctk.CTkFrame(body, fg_color="transparent")
        stats.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1)

        project_count = len(find_projects())
        can_launch = self.user.can_launch_water_demand()
        self._stat_card(stats, 0, "Saved Projects", str(project_count), "In database")
        self._stat_card(stats, 1, "Active Users", str(count_active_users()), "Registered accounts")
        self._stat_card(
            stats, 2, "Your Role", self.user.role_label,
            "Engineer access" if can_launch else "View only",
        )

        self.project_hub = ProjectHub(
            body,
            user=self.user,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
            enabled=can_launch,
        )
        self.project_hub.grid(row=3, column=0, sticky="ew", pady=(0, 16))

        module_card = ctk.CTkFrame(body, fg_color="white", corner_radius=10, border_width=1, border_color="#DDDDDD")
        module_card.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        ctk.CTkLabel(
            module_card,
            text="Water Demand Calculator",
            font=("Arial", 15, "bold"),
            text_color=BRAND_NAVY,
        ).pack(anchor="w", padx=20, pady=(16, 4))
        ctk.CTkLabel(
            module_card,
            text="Open the calculator with a blank session (use Project Management above to load a saved project).",
            font=("Arial", 11),
            text_color="#666666",
            justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 12))
        ctk.CTkButton(
            module_card,
            text="Launch Calculator (Blank)",
            command=self._launch_water_demand,
            fg_color=BRAND_ORANGE if can_launch else "#AAAAAA",
            hover_color="#D06018" if can_launch else "#AAAAAA",
            state="normal" if can_launch else "disabled",
            height=36,
        ).pack(anchor="w", padx=20, pady=(0, 16))

        if not can_launch:
            ctk.CTkLabel(
                body,
                text="Your account has Viewer access. Contact an administrator for project access.",
                font=("Arial", 12),
                text_color="#C0392B",
            ).grid(row=5, column=0, sticky="w", pady=(8, 0))

    def _stat_card(self, parent, column: int, title: str, value: str, subtitle: str) -> None:
        card = ctk.CTkFrame(parent, corner_radius=10, fg_color="white", border_width=1, border_color="#DDDDDD")
        card.grid(row=0, column=column, padx=6, pady=4, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=("Arial", 12, "bold"), text_color=BRAND_NAVY).pack(
            anchor="w", padx=16, pady=(14, 4)
        )
        ctk.CTkLabel(card, text=value, font=("Arial", 24, "bold"), text_color=BRAND_ORANGE).pack(
            anchor="w", padx=16, pady=(0, 2)
        )
        ctk.CTkLabel(card, text=subtitle, font=("Arial", 10), text_color="#888888").pack(
            anchor="w", padx=16, pady=(0, 14)
        )

    def _launch_water_demand(self) -> None:
        if not self.user.can_launch_water_demand():
            messagebox.showwarning("Access Denied", "Your role does not have permission to launch this module.")
            return
        self.on_launch_water_demand()

    def _confirm_logout(self) -> None:
        if messagebox.askyesno("Logout", "Are you sure you want to logout?"):
            self.on_logout()

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()
