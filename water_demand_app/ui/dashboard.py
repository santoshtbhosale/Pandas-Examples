from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from ui.gui_safe import safe_command
from ui.project_hub import ProjectHub


class MainDashboard(ctk.CTkFrame):
    """Professional Project Home dashboard."""

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
        self._stat_labels: dict[str, ctk.CTkLabel] = {}
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
        content.grid(row=0, column=0, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)

        hero = ctk.CTkFrame(content, fg_color=BRAND_NAVY, corner_radius=16)
        hero.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 18))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(28, 20), pady=24)
        ctk.CTkLabel(
            left,
            text="AMERICAN EDGE ENGINEERS",
            font=("Arial", 11, "bold"),
            text_color="#AFC3D6",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Project Home",
            font=("Arial", 25, "bold"),
            text_color="white",
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))
        ctk.CTkLabel(
            left,
            text="Manage and monitor your engineering projects.",
            font=("Arial", 12),
            text_color="#D7E1EA",
            anchor="w",
        ).pack(anchor="w", pady=(7, 0))

        ctk.CTkButton(
            hero,
            text="+ New Project",
            command=safe_command(self.on_new_project, parent=self),
            fg_color="#20A968",
            hover_color="#1B8F58",
            width=150,
            height=40,
            font=("Arial", 12, "bold"),
        ).grid(row=0, column=1, padx=(10, 28), pady=24, sticky="e")

        ctk.CTkLabel(
            content,
            text="PROJECT OVERVIEW",
            font=("Arial", 12, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=1, column=0, sticky="w", padx=28, pady=(0, 8))

        stats_row_1 = ctk.CTkFrame(content, fg_color="transparent")
        stats_row_1.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 8))
        stats_row_1.grid_columnconfigure((0, 1, 2), weight=1)

        stats_row_2 = ctk.CTkFrame(content, fg_color="transparent")
        stats_row_2.grid(row=3, column=0, sticky="ew", padx=28, pady=(0, 16))
        stats_row_2.grid_columnconfigure((0, 1, 2), weight=1)

        stat_defs = [
            ("total", "TOTAL PROJECTS", stats_row_1, 0),
            ("in_progress", "IN PROGRESS", stats_row_1, 1),
            ("completed", "COMPLETED", stats_row_1, 2),
            ("pending", "PENDING", stats_row_2, 0),
            ("delayed", "DELAYED", stats_row_2, 1),
            ("today", "TODAY'S PROJECTS", stats_row_2, 2),
        ]
        for key, title, parent, column in stat_defs:
            self._stat_labels[key] = self._make_stat_card(parent, column, title, "0")

        self.project_hub = ProjectHub(
            content,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
            on_edit_project=self.on_open_project,
            on_stats_changed=self._update_stats,
        )
        self.project_hub.grid(row=4, column=0, sticky="nsew", padx=28, pady=(0, 26))

    def _make_stat_card(self, parent, column: int, title: str, value: str):
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
        ctk.CTkLabel(card, text=title, font=("Arial", 9, "bold"), text_color="#7A8794").pack(
            anchor="w", padx=16, pady=(12, 0)
        )
        value_label = ctk.CTkLabel(card, text=value, font=("Arial", 22, "bold"), text_color=BRAND_NAVY)
        value_label.pack(anchor="w", padx=16, pady=(2, 12))
        return value_label

    def _update_stats(self, stats: dict) -> None:
        mapping = {
            "total": stats.get("total", 0),
            "in_progress": stats.get("in_progress", 0),
            "completed": stats.get("completed", 0),
            "pending": stats.get("pending", 0),
            "delayed": stats.get("delayed", 0),
            "today": stats.get("today", 0),
        }
        for key, value in mapping.items():
            label = self._stat_labels.get(key)
            if label is not None:
                label.configure(text=str(value))

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()


DashboardScreen = MainDashboard
