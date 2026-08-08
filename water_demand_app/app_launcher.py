"""Application entry point — Splash → Login → Dashboard → Water Demand."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from models.user import UserSession
from services.auth_db import init_users_table
from services.database import DB_PATH, init_db
from services.lookup_db import init_lookup_tables
from ui.dashboard import DashboardScreen
from ui.login_screen import LoginScreen
from ui.splash_screen import SplashScreen


class Application(ctk.CTk):
    """Root shell managing authentication flow and module launch."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        self.title("American Edge Engineers — Water Demand Software")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color="#F0F2F5")

        init_db(DB_PATH)
        init_lookup_tables(DB_PATH)
        init_users_table(DB_PATH)

        self.current_user: Optional[UserSession] = None
        self._water_app = None
        self._active_screen = None

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
        self._clear_screen()
        self._active_screen = LoginScreen(self, on_login_success=self._on_login_success)
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _on_login_success(self, user: UserSession) -> None:
        self.current_user = user
        self._show_dashboard()

    def _show_dashboard(self) -> None:
        self._clear_screen()
        self._active_screen = DashboardScreen(
            self,
            user=self.current_user,
            on_launch_water_demand=self._launch_water_demand,
            on_logout=self._logout,
        )
        self._active_screen.grid(row=0, column=0, sticky="nsew")

    def _launch_water_demand(self) -> None:
        if self.current_user is None:
            return
        self.withdraw()
        self._water_app = WaterDemandApp(
            current_user=self.current_user,
            on_logout=self._on_water_app_logout,
        )
        self._water_app.protocol("WM_DELETE_WINDOW", self._on_water_app_close)

    def _on_water_app_close(self) -> None:
        if self._water_app is not None:
            try:
                if self._water_app._autosave_job is not None:
                    self._water_app.after_cancel(self._water_app._autosave_job)
            except Exception:
                pass
            self._water_app.destroy()
            self._water_app = None
        self.deiconify()
        if isinstance(self._active_screen, DashboardScreen):
            self._active_screen.refresh_stats()

    def _on_water_app_logout(self) -> None:
        self._on_water_app_close()
        self._logout()

    def _logout(self) -> None:
        self.current_user = None
        self._show_login()
        if isinstance(self._active_screen, LoginScreen):
            self._active_screen.reset()


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
