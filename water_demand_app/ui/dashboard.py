from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from services.project_service import find_projects
from ui.gui_safe import safe_command
from ui.project_hub import ProjectHub


class MainDashboard(ctk.CTkFrame):
    """Professional, simplified Project Home dashboard."""

    def __init__(
        self,
        master,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="#F4F6F8")
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_exit = on_exit
        self.project_hub: Optional[ProjectHub] = None
        self._project_count = 0
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        content = ctk.CTkScrollableFrame(
            self,
            fg_color="#F4F6F8",
            corner_radius=0,
            scrollbar_button_color="#AAB4BE",
            scrollbar_button_hover_color="#7F8C97",
        )
        content.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        content.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(content, fg_color=BRAND_NAVY, corner_radius=16, border_width=0)
        hero.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 18))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(28, 20), pady=24)
        ctk.CTkLabel(
            left,
            text="Project Home",
            font=("Arial", 25, "bold"),
            text_color="white",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Create, open and manage your engineering projects.",
            font=("Arial", 12),
            text_color="#D7E1EA",
            anchor="w",
        ).pack(anchor="w", pady=(7, 0))
        ctk.CTkLabel(
            left,
            text="To start a new engineering report, click New Project.",
            font=("Arial", 11),
            text_color="#AFC3D6",
            anchor="w",
        ).pack(anchor="w", pady=(7, 0))

        version = ctk.CTkLabel(
            hero,
            text="v2.0",
            font=("Arial", 11, "bold"),
            text_color=BRAND_ORANGE,
            fg_color="#102E4B",
            corner_radius=12,
            width=64,
            height=30,
        )
        version.grid(row=0, column=1, padx=(10, 28), pady=24, sticky="e")

        actions_card = ctk.CTkFrame(
            content,
            fg_color="white",
            corner_radius=14,
            border_width=1,
            border_color="#E0E5EA",
        )
        actions_card.grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 16))
        actions_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(
            actions_card,
            text="Quick Start",
            font=("Arial", 15, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=20, pady=(16, 10))

        quick = [
            ("+  New Project", "Start a new engineering calculation", "#20A968", self.on_new_project),
            ("Open Project", "Continue an existing project", BRAND_ORANGE, self._open_selected_prompt),
            ("Search Projects", "Find saved projects quickly", "#2F80B8", self._focus_search),
            ("Reports", "Generate PDF and Excel reports", "#7F8C8D", self._reports_info),
        ]
        for i, (title, subtitle, color, cmd) in enumerate(quick):
            card = ctk.CTkFrame(
                actions_card,
                fg_color="#F7F9FB",
                corner_radius=10,
                border_width=1,
                border_color="#E4E9EE",
            )
            card.grid(
                row=1,
                column=i,
                sticky="ew",
                padx=(20 if i == 0 else 7, 7 if i < 3 else 20),
                pady=(0, 18),
            )
            card.grid_columnconfigure(0, weight=1)
            ctk.CTkButton(
                card,
                text=title,
                command=safe_command(cmd, parent=self),
                fg_color=color,
                hover_color=color,
                height=42,
                corner_radius=8,
                font=("Arial", 12, "bold"),
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 7))
            ctk.CTkLabel(
                card,
                text=subtitle,
                font=("Arial", 10),
                text_color="#6B7280",
            ).grid(row=1, column=0, pady=(0, 12))

        stats_row = ctk.CTkFrame(content, fg_color="transparent")
        stats_row.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 16))
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)

        self._stat_total = self._make_stat_card(stats_row, 0, "TOTAL PROJECTS", "0", "All saved projects")
        self._stat_latest = self._make_stat_card(stats_row, 1, "LATEST PROJECT", "—", "Most recently updated")
        self._stat_info = self._make_stat_card(stats_row, 2, "WORKFLOW", "Auto", "Calculations update automatically")

        self.project_hub = ProjectHub(
            content,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
        )
        self.project_hub.grid(row=3, column=0, sticky="nsew", padx=28, pady=(0, 26))

        self._refresh_stats()

    def _make_stat_card(self, parent, column: int, title: str, value: str, subtitle: str):
        card = ctk.CTkFrame(
            parent,
            fg_color="white",
            corner_radius=12,
            border_width=1,
            border_color="#E0E5EA",
            height=88,
        )
        card.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 6 if column < 2 else 0))
        card.grid_propagate(False)
        card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(card, text=title, font=("Arial", 9, "bold"), text_color="#7A8794").grid(
            row=0, column=0, sticky="w", padx=16, pady=(11, 0)
        )
        value_label = ctk.CTkLabel(card, text=value, font=("Arial", 17, "bold"), text_color=BRAND_NAVY)
        value_label.grid(row=1, column=0, sticky="w", padx=16)
        ctk.CTkLabel(card, text=subtitle, font=("Arial", 9), text_color="#8A949E").grid(
            row=2, column=0, sticky="w", padx=16, pady=(0, 8)
        )
        return value_label

    def _open_selected_prompt(self) -> None:
        if self.project_hub and self.project_hub._selected_id:
            self.on_open_project(self.project_hub._selected_id)
        else:
            if self.project_hub:
                self.project_hub.focus_search()
            messagebox.showinfo(
                "Open Project",
                "Select a project from the list below, then click Open Project.",
            )

    def _focus_search(self) -> None:
        if self.project_hub:
            self.project_hub.focus_search()

    def _reports_info(self) -> None:
        messagebox.showinfo(
            "Reports",
            "Open a project and use Preview → Generate Report to create PDF and Excel outputs.",
        )

    def _refresh_stats(self) -> None:
        projects = find_projects()
        self._project_count = len(projects)
        if hasattr(self, "_stat_total"):
            self._stat_total.configure(text=str(self._project_count))
        if hasattr(self, "_stat_latest"):
            if projects:
                latest = projects[0]
                name = (latest.get("project_name") or "Untitled").strip()
                self._stat_latest.configure(text=name[:22] + ("…" if len(name) > 22 else ""))
            else:
                self._stat_latest.configure(text="—")

    def refresh_stats(self) -> None:
        self._refresh_stats()
        if self.project_hub:
            self.project_hub.refresh()


DashboardScreen = MainDashboard
