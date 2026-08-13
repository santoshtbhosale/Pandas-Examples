"""Application entry point — Splash → Project Home → unified project workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from config.nbc_2026 import BRAND_NAVY, BRAND_ORANGE, is_project_type_set, project_type_label
from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from services.project_service import create_new_project_state, load_project_state, persist_project_state
from ui.app_state import AppState
from ui.dashboard import MainDashboard
from ui.gui_safe import safe_command
from ui.splash_screen import SplashScreen

APP_VERSION = "2.0.0"
APP_TITLE = "PlanetCode Engineering Suite"


class Application(ctk.CTk):
    """Single main window: dashboard and project workflow share one shell."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1280x850")
        self.minsize(1100, 700)
        self.configure(fg_color="#F0F2F5")

        init_db(DB_PATH)
        init_lookup_tables(DB_PATH)

        self._workspace = None
        self._dashboard: Optional[MainDashboard] = None
        self._mode = "splash"
        self._last_saved_at = ""
        self._autosave_job = None

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_shell()
        self._show_splash()

    def _build_shell(self) -> None:
        self.header = ctk.CTkFrame(self, fg_color=BRAND_NAVY, corner_radius=0, height=56)
        self.header.grid(row=0, column=0, sticky="ew")
        self.header.grid_propagate(False)
        self.header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            self.header,
            text="AMERICAN EDGE ENGINEERS",
            font=("Arial", 13, "bold"),
            text_color=BRAND_ORANGE,
        ).grid(row=0, column=0, padx=16, pady=8, sticky="w")
        ctk.CTkLabel(
            self.header,
            text="Water Demand Report Generator",
            font=("Arial", 11),
            text_color="#CCCCCC",
        ).grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        self.header_meta = ctk.CTkLabel(
            self.header,
            text="Project Home",
            font=("Arial", 11),
            text_color="white",
            anchor="e",
        )
        self.header_meta.grid(row=0, column=1, rowspan=2, padx=16, sticky="e")

        self.body = ctk.CTkFrame(self, fg_color="#F0F2F5", corner_radius=0)
        self.body.grid(row=1, column=0, sticky="nsew")
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.status_bar = ctk.CTkFrame(self, fg_color="#E8ECF0", corner_radius=0, height=28)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.grid_propagate(False)
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Auto Calculation: ON  |  Ready",
            font=("Arial", 10),
            text_color="#555555",
            anchor="w",
        )
        self.status_label.pack(side="left", padx=12, pady=4)

    def _update_status(self) -> None:
        if self._workspace is not None and self._mode == "project":
            pid = self._workspace.app_state.project.project_id
            saved = f"Last Saved: {self._last_saved_at}" if self._last_saved_at else "Last Saved: —"
            self.status_label.configure(text=f"Project ID: {pid}  |  Auto Calculation: ON  |  {saved}")
        else:
            self.status_label.configure(text="Auto Calculation: ON  |  Project Home")

    def _update_header_meta(self) -> None:
        if self._workspace is not None and self._mode == "project":
            p = self._workspace.app_state.project
            ptype = project_type_label(p.project_type) if is_project_type_set(p.project_type) else "—"
            self.header_meta.configure(
                text=f"{p.project_name or 'Untitled'}  |  {p.project_id}  |  {ptype}"
            )
        else:
            self.header_meta.configure(text="Project Home")

    def _clear_body(self) -> None:
        for child in self.body.winfo_children():
            child.grid_remove()

    def _show_splash(self) -> None:
        self._mode = "splash"
        self._clear_body()
        splash = SplashScreen(self.body, on_complete=self._show_dashboard)
        splash.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _show_dashboard(self) -> None:
        self._mode = "dashboard"
        self._clear_body()
        if self._workspace is not None:
            self._workspace.grid_remove()
        self._dashboard = MainDashboard(
            self.body,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_open_project=safe_command(self._open_project, parent=self),
            on_exit=self._exit_application,
        )
        self._dashboard.grid(row=0, column=0, sticky="nsew")
        self._update_header_meta()
        self._update_status()

    def _ensure_workspace(self):
        if self._workspace is not None:
            return self._workspace
        from _app_sidebar import ProjectWorkspace

        self._workspace = ProjectWorkspace(
            self.body,
            on_home=safe_command(self._show_dashboard, parent=self),
            on_autosave=self._on_project_autosaved,
            on_header_update=self._on_workspace_header_update,
        )
        return self._workspace

    def _show_project(self, state: AppState) -> None:
        ws = self._ensure_workspace()
        if self._dashboard is not None:
            self._dashboard.grid_remove()
        ws.grid(row=0, column=0, sticky="nsew")
        ws.ensure_pages_built()
        ws.apply_state(state)
        self._mode = "project"
        self._schedule_autosave()
        self._update_header_meta()
        self._update_status()

    def _start_new_project(self) -> None:
        state = create_new_project_state(DB_PATH)
        self._show_project(state)

    def _open_project(self, project_id: str) -> None:
        try:
            state = load_project_state(project_id, DB_PATH)
        except ValueError as exc:
            messagebox.showerror("Open Project", str(exc))
            return
        self._show_project(state)

    def _exit_application(self) -> None:
        if self._workspace is not None:
            try:
                self._workspace.autosave_before_close()
            except Exception:
                pass
        self.destroy()

    def _on_workspace_header_update(self) -> None:
        self._update_header_meta()
        self._update_status()

    def _on_project_autosaved(self) -> None:
        self._last_saved_at = datetime.now().strftime("%H:%M:%S")
        self._update_status()
        if self._dashboard is not None:
            self._dashboard.refresh_stats()

    def _schedule_autosave(self) -> None:
        if self._autosave_job is not None:
            self.after_cancel(self._autosave_job)
        self._autosave_job = self.after(120_000, self._auto_save_tick)

    def _auto_save_tick(self) -> None:
        if self._workspace is not None and self._mode == "project":
            try:
                self._workspace.autosave_before_close()
                self._on_project_autosaved()
            except Exception:
                pass
        self._schedule_autosave()


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
