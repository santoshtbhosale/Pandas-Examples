from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE
from services.project_service import find_projects
from ui.gui_safe import safe_command
from ui.project_hub import ProjectHub


class MainDashboard(ctk.CTkFrame):
    """Main engineering dashboard — project home (no authentication)."""

    def __init__(
        self,
        master,
        on_new_project: Callable[[], None],
        on_open_project: Callable[[str], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(master, fg_color="#F0F2F5")
        self.on_new_project = on_new_project
        self.on_open_project = on_open_project
        self.on_exit = on_exit
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
            top, text="PLANETCODE ENGINEERING SUITE",
            font=("Arial", 16, "bold"), text_color=BRAND_ORANGE,
        ).grid(row=0, column=0, padx=24, pady=20, sticky="w")
        ctk.CTkLabel(
            top, text="Engineering Design & Reporting",
            font=("Arial", 11), text_color="#CCCCCC",
        ).grid(row=0, column=1, padx=16, sticky="w")
        ctk.CTkButton(
            top, text="Exit", command=self.on_exit,
            fg_color="#C0392B", width=80, height=32,
        ).grid(row=0, column=2, padx=24, sticky="e")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body, text="Project Home",
            font=("Arial", 24, "bold"), text_color=BRAND_NAVY, anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))
        ctk.CTkLabel(
            body,
            text="Create, open, and manage engineering projects. Calculations update automatically.",
            font=("Arial", 13), text_color="#666666", anchor="w",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 16))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        for i, (text, color, cmd) in enumerate([
            ("+ New Project", "#27AE60", self.on_new_project),
            ("Open Existing Project", BRAND_ORANGE, self._open_selected_prompt),
            ("Search Project", "#2980B9", self._focus_search),
            ("Reports", "#7F8C8D", self._reports_info),
        ]):
            ctk.CTkButton(
                actions, text=text, fg_color=color, height=40,
                command=safe_command(cmd, parent=self),
            ).grid(row=0, column=i, padx=4, sticky="ew")
            actions.grid_columnconfigure(i, weight=1)

        stats = ctk.CTkFrame(body, fg_color="white", corner_radius=10, border_width=1, border_color="#DDDDDD")
        stats.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        count = len(find_projects())
        ctk.CTkLabel(
            stats, text=f"Saved Projects: {count}",
            font=("Arial", 14, "bold"), text_color=BRAND_NAVY,
        ).pack(anchor="w", padx=20, pady=16)

        self.project_hub = ProjectHub(
            body,
            on_new_project=self.on_new_project,
            on_open_project=self.on_open_project,
        )
        self.project_hub.grid(row=4, column=0, sticky="ew", pady=(0, 16))

    def _open_selected_prompt(self) -> None:
        if self.project_hub and self.project_hub._selected_id:
            self.on_open_project(self.project_hub._selected_id)
        else:
            messagebox.showinfo("Open Project", "Select a project from Project History, then click Open.")

    def _focus_search(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()

    def _reports_info(self) -> None:
        messagebox.showinfo(
            "Reports",
            "Open a project and use Preview → Generate Report to create PDF and Excel outputs.",
        )

    def refresh_stats(self) -> None:
        if self.project_hub:
            self.project_hub.refresh()
