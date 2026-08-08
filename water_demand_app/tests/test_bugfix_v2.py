"""Regression tests for v2.0 bug fixes — login, engineer dashboard, create user."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from models.user import ROLE_ENGINEER, ROLE_SUPER_ADMIN, ROLE_TEAM_LEADER
from services.auth_db import (
    authenticate,
    create_user,
    get_user_by_username,
    init_users_table,
    list_users,
    username_exists,
    verify_password,
)
from services.database import init_db
from ui.dashboard_router import create_dashboard
from ui.gui_safe import safe_command


class TestUsernameValidation(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)
        init_users_table(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_username_exists_detects_duplicate(self) -> None:
        self.assertTrue(username_exists("admin", db_path=self.db_path))
        self.assertFalse(username_exists("brandnew", db_path=self.db_path))

    def test_create_user_hashes_password(self) -> None:
        leader = next(u for u in list_users(self.db_path) if u.role == ROLE_TEAM_LEADER)
        user_id = create_user(
            "neweng",
            "Test@1234",
            "New Engineer",
            ROLE_ENGINEER,
            employee_id="EMP-999",
            team="Design Team",
            team_leader_id=leader.user_id,
            db_path=self.db_path,
        )
        self.assertGreater(user_id, 0)
        record = get_user_by_username("neweng", self.db_path)
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.role, ROLE_ENGINEER)
        self.assertEqual(record.team_leader_id, leader.user_id)
        session = authenticate("neweng", "Test@1234", self.db_path)
        self.assertIsNotNone(session)

    def test_duplicate_username_rejected(self) -> None:
        create_user("dupuser", "Pass@123", "Dup User", ROLE_ENGINEER, employee_id="E1", db_path=self.db_path)
        with self.assertRaises(Exception):
            create_user("dupuser", "Pass@456", "Dup User 2", ROLE_ENGINEER, employee_id="E2", db_path=self.db_path)


class TestSafeCallbacks(unittest.TestCase):
    def test_safe_command_catches_exception(self) -> None:
        from unittest.mock import patch

        called = {"value": False}

        def bad() -> None:
            called["value"] = True
            raise RuntimeError("boom")

        wrapped = safe_command(bad)
        with patch("ui.gui_safe.messagebox.showerror"):
            wrapped()
        self.assertTrue(called["value"])


class TestDashboardRouting(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db_path = self._tmp.name
        init_db(self.db_path)
        init_users_table(self.db_path)

    def tearDown(self) -> None:
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_engineer_dashboard_callbacks_do_not_raise(self) -> None:
        user = authenticate("akash", "Akash@123", self.db_path)
        self.assertIsNotNone(user)
        events = {"new": 0, "open": 0, "launch": 0, "logout": 0}

        def on_new() -> None:
            events["new"] += 1

        def on_open(pid: str) -> None:
            events["open"] += 1

        def on_launch() -> None:
            events["launch"] += 1

        def on_logout() -> None:
            events["logout"] += 1

        dash = create_dashboard(
            self.root,
            user=user,
            on_new_project=safe_command(on_new, parent=self.root),
            on_open_project=safe_command(on_open, parent=self.root),
            on_launch_water_demand=safe_command(on_launch, parent=self.root),
            on_logout=safe_command(on_logout, parent=self.root),
        )
        dash.update_idletasks()
        self.assertEqual(dash.__class__.__name__, "EngineerDashboard")
        if hasattr(dash, "on_new_project"):
            dash.on_new_project()
        if hasattr(dash, "on_launch_water_demand"):
            dash.on_launch_water_demand()
        self.assertEqual(events["new"], 1)
        self.assertEqual(events["launch"], 1)
        dash.destroy()

    def test_super_admin_dashboard_class(self) -> None:
        user = authenticate("superadmin", "Super@123", self.db_path)
        self.assertIsNotNone(user)
        dash = create_dashboard(
            self.root,
            user=user,
            on_new_project=lambda: None,
            on_open_project=lambda _pid: None,
            on_launch_water_demand=lambda: None,
            on_logout=lambda: None,
        )
        self.assertEqual(dash.__class__.__name__, "SuperAdminDashboard")
        dash.destroy()


class TestLoginScreen(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_login_screen_renders(self) -> None:
        from ui.login_screen import LoginScreen

        screen = LoginScreen(self.root, on_login_success=lambda _u: None)
        screen.grid(row=0, column=0)
        screen.update_idletasks()
        self.assertTrue(screen.username_entry.winfo_exists())
        self.assertTrue(screen.password_entry.winfo_exists())
        self.assertIn("LOGIN", screen.login_btn.cget("text"))
        screen.destroy()

    def test_invalid_login_shows_error_without_closing(self) -> None:
        from ui.login_screen import LoginScreen

        screen = LoginScreen(self.root, on_login_success=lambda _u: None)
        screen.grid(row=0, column=0)
        screen.username_entry.insert(0, "baduser")
        screen.password_entry.insert(0, "badpass")
        screen._attempt_login()
        screen.update_idletasks()
        self.assertIn("Invalid username or password", screen.error_label.cget("text"))
        self.assertTrue(self.root.winfo_exists())
        screen.destroy()


class TestWaterDemandToplevel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from _app_sidebar import WaterDemandApp

            cls.ctk = ctk
            cls.WaterDemandApp = WaterDemandApp
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_embedded_water_demand_does_not_destroy_parent(self) -> None:
        app = self.WaterDemandApp(master=self.root)
        app.withdraw()
        app.update_idletasks()
        self.assertTrue(self.root.winfo_exists())
        app.destroy()
        self.assertTrue(self.root.winfo_exists())

    def test_standalone_water_demand_still_works(self) -> None:
        app = self.WaterDemandApp()
        app.withdraw()
        app.update_idletasks()
        self.assertIn("Project", app.pages)
        app.destroy()


class TestCreateUserDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_create_user_dialog_opens(self) -> None:
        from ui.create_user_dialog import CreateUserDialog

        dialog = CreateUserDialog(self.root, actor_username="superadmin")
        dialog.update_idletasks()
        self.assertTrue(dialog.winfo_exists())
        self.assertIn("Create User", dialog.title())
        dialog.destroy()


if __name__ == "__main__":
    unittest.main()
