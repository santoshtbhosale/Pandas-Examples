"""Application entry point — Splash → Main Dashboard → Water Demand."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from services.project_service import create_new_project_state, load_project_state
from ui.app_state import AppState
from ui.dashboard import MainDashboard
from ui.gui_safe import safe_command
from ui.splash_screen import SplashScreen

APP_VERSION = "2.0.0"
APP_TITLE = "PlanetCode Engineering Suite"


class Application(ctk.CTk):
    """Root shell — engineering design & reporting (no authentication)."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_TITLE} v{APP_VERSION}")
        self.geometry("1100x780")
        self.minsize(900, 650)
        self.configure(fg_color="#F0F2F5")

        init_db(DB_PATH)
        init_lookup_tables(DB_PATH)

        self._water_app = None
        self._active_screen = None
        self._pending_state: Optional[AppState] = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._show_splash()

    def _clear_screen(self) -> None:
        if self._active_screen is not None:
            self._active_screen.destroy()
            self._active_screen = None

    def _show_splash(self) -> None:
        self._clear_screen()
        self._active_screen = SplashScreen(self, on_complete=self._show_dashboard)
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _show_dashboard(self) -> None:
        self._clear_screen()
        self._active_screen = MainDashboard(
            self,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_open_project=safe_command(self._open_project, parent=self),
            on_exit=self._exit_application,
        )
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _exit_application(self) -> None:
        self.destroy()

    def _start_new_project(self) -> None:
        self._pending_state = create_new_project_state(DB_PATH)
        self._launch_water_demand(self._pending_state)

    def _open_project(self, project_id: str) -> None:
        try:
            self._pending_state = load_project_state(project_id, DB_PATH)
        except ValueError as exc:
            from tkinter import messagebox
            messagebox.showerror("Open Project", str(exc))
            return
        self._launch_water_demand(self._pending_state)

    def _launch_water_demand(self, initial_state: Optional[AppState]) -> None:
        from _app_sidebar import WaterDemandApp

        self.withdraw()
        self._water_app = WaterDemandApp(
            master=self,
            initial_state=initial_state,
            on_close=self._on_water_app_close,
            on_autosave=self._on_project_autosaved,
        )
        self._water_app.protocol("WM_DELETE_WINDOW", self._on_water_app_close)
        self._water_app.focus_force()

    def _on_project_autosaved(self) -> None:
        if hasattr(self._active_screen, "refresh_stats"):
            self._active_screen.refresh_stats()

    def _on_water_app_close(self) -> None:
        if self._water_app is not None:
            try:
                self._water_app._autosave_before_close()
                if self._water_app._autosave_job is not None:
                    self._water_app.after_cancel(self._water_app._autosave_job)
            except Exception:
                pass
            self._water_app.destroy()
            self._water_app = None
        self.deiconify()
        if hasattr(self._active_screen, "refresh_stats"):
            self._active_screen.refresh_stats()


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
