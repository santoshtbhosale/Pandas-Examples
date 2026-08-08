"""Application entry point — Splash → Login → Dashboard → Water Demand."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from models.user import UserSession
from services.audit_service import ACTION_LOGOUT, log_audit
from services.auth_db import init_users_table
from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from services.project_service import create_new_project_state, load_project_state, persist_project_state
from services.project_workflow_service import init_engineer_owned_project
from services.session_service import SessionContext
from ui.app_state import AppState
from ui.dashboard_router import create_dashboard
from ui.gui_safe import safe_command
from ui.login_screen import LoginScreen
from ui.session_manager import SessionManager
from ui.splash_screen import SplashScreen

APP_VERSION = "2.0.0"
APP_TITLE = "PlanetCode Engineering Suite"


class Application(ctk.CTk):
    """Root shell managing authentication flow and module launch."""

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
        init_users_table(DB_PATH)

        self.current_user: Optional[UserSession] = None
        self.session: Optional[SessionContext] = None
        self._session_manager: Optional[SessionManager] = None
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
        self._active_screen = SplashScreen(self, on_complete=self._show_login)
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _show_login(self) -> None:
        self._stop_session()
        self._clear_screen()
        self._active_screen = LoginScreen(
            self,
            on_login_success=self._on_login_success,
            on_exit=self._exit_application,
        )
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _exit_application(self) -> None:
        self._stop_session()
        self.destroy()

    def _stop_session(self) -> None:
        if self._session_manager is not None:
            self._session_manager.stop()
            self._session_manager = None

    def _on_login_success(self, user: UserSession) -> None:
        self.current_user = user
        self.session = SessionContext.from_user(user)
        self._start_session()
        self._show_dashboard()

    def _start_session(self) -> None:
        self._stop_session()
        self._session_manager = SessionManager(
            self,
            get_user=lambda: self.current_user,
            on_logout=safe_command(self._logout, parent=self),
        )
        self._session_manager.start()

    def _show_dashboard(self) -> None:
        self._clear_screen()
        self._active_screen = create_dashboard(
            self,
            user=self.current_user,
            session=self.session,
            on_new_project=safe_command(self._start_new_project, parent=self),
            on_open_project=safe_command(self._open_project, parent=self),
            on_launch_water_demand=safe_command(self._launch_blank, parent=self),
            on_logout=safe_command(self._logout, parent=self),
        )
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _start_new_project(self) -> None:
        if self.current_user is None:
            return
        self._pending_state = create_new_project_state(self.current_user, DB_PATH)
        if self.current_user.is_engineer():
            persist_project_state(self._pending_state, self.current_user, DB_PATH)
            init_engineer_owned_project(self._pending_state.project.project_id, self.current_user, DB_PATH)
        self._launch_water_demand(self._pending_state)

    def _open_project(self, project_id: str) -> None:
        if self.current_user is None:
            return
        try:
            self._pending_state = load_project_state(project_id, DB_PATH, user=self.current_user)
        except ValueError as exc:
            from tkinter import messagebox
            messagebox.showerror("Open Project", str(exc))
            return
        self._launch_water_demand(self._pending_state)

    def _launch_blank(self) -> None:
        if self.current_user is None:
            return
        self._pending_state = None
        self._launch_water_demand(None)

    def _launch_water_demand(self, initial_state: Optional[AppState]) -> None:
        if self.current_user is None:
            return
        from _app_sidebar import WaterDemandApp

        self.withdraw()
        self._water_app = WaterDemandApp(
            master=self,
            current_user=self.current_user,
            on_logout=self._on_water_app_logout,
            initial_state=initial_state,
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

    def _on_water_app_logout(self) -> None:
        self._on_water_app_close()
        self._logout()

    def _logout(self) -> None:
        if self.current_user is not None:
            log_audit(
                ACTION_LOGOUT,
                username=self.current_user.username,
                user_id=self.current_user.user_id,
            )
        self._stop_session()
        self.current_user = None
        self.session = None
        self._pending_state = None
        self._show_login()
        if isinstance(self._active_screen, LoginScreen):
            self._active_screen.reset()


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
