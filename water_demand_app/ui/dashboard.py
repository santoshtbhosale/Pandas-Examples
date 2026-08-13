from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from ui.gui_safe import safe_command
from ui.project_hub import ProjectHub


class MainDashboard(ctk.CTkFrame):
    """Fixed-height Project Home dashboard — only the project table scrolls."""

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
        self.grid_rowconfigure(3, weight=1)

        hero = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=12)
        hero.grid(row=0, column=0, sticky="ew", padx=20, pady=(14, 8))
        hero.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(18, 12), pady=14)
        ctk.CTkLabel(
            left,
            text="AMERICAN EDGE ENGINEERS",
            font=("Arial", 10, "bold"),
            text_color="#AFC3D6",
            anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            left,
            text="Project Home",
            font=("Arial", 22, "bold"),
            text_color="white",
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(
            left,
            text="Manage and monitor your engineering projects.",
            font=("Arial", 11),
            text_color="#D7E1EA",
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        ctk.CTkButton(
            hero,
            text="+ New Project",
            command=safe_command(self.on_new_project, parent=self),
            fg_color="#20A968",
            hover_color="#1B8F58",
            width=140,
            height=36,
            font=("Arial", 11, "bold"),
        ).grid(row=0, column=1, padx=(8, 18), pady=14, sticky="e")

        ctk.CTkLabel(
            self,
            text="PROJECT OVERVIEW",
            font=("Arial", 11, "bold"),
            text_color=BRAND_NAVY,
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 4))

        stats_row = ctk.CTkFrame(self, fg_color="transparent")
        stats_row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        for i in range(5):
            stats_row.grid_columnconfigure(i, weight=1)

        for column, (key, title) in enumerate([
            ("total", "TOTAL PROJECTS"),
            ("in_progress", "IN PROGRESS"),
            ("completed", "COMPLETED"),
            ("pending", "PENDING"),
            ("delayed", "DELAYED"),
        ]):
            self._stat_labels[key] = self._make_stat_card(stats_row, column, title, "0")

        self.project_hub = ProjectHub(
            self,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
            on_edit_project=self.on_open_project,
            on_stats_changed=self._update_stats,
        )
        self.project_hub.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 12))

    def _make_stat_card(self, parent, column: int, title: str, value: str):
        card = ctk.CTkFrame(
            parent,
            fg_color="white",
            corner_radius=10,
            border_width=1,
            border_color="#E0E5EA",
            height=62,
        )
        card.grid(
            row=0,
            column=column,
            sticky="ew",
            padx=(0 if column == 0 else 4, 4 if column < 4 else 0),
        )
        card.grid_propagate(False)
        ctk.CTkLabel(card, text=title, font=("Arial", 8, "bold"), text_color="#7A8794").pack(
            anchor="w", padx=12, pady=(8, 0)
        )
        value_label = ctk.CTkLabel(card, text=value, font=("Arial", 18, "bold"), text_color=BRAND_NAVY)
        value_label.pack(anchor="w", padx=12, pady=(0, 8))
        return value_label

    def _update_stats(self, stats: dict) -> None:
        mapping = {
            "total": stats.get("total", 0),
            "in_progress": stats.get("in_progress", 0),
            "completed": stats.get("completed", 0),
            "pending": stats.get("pending", 0),
            "delayed": stats.get("delayed", 0),
        }
        for key, value in mapping.items():
            label = self._stat_labels.get(key)
            if label is not None:
                label.configure(text=str(value))

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()


DashboardScreen = MainDashboard
