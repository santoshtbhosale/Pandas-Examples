"""Regression tests for login workflow, role security, session, and ownership."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from models.user import ROLE_ENGINEER, ROLE_LABELS
from services.audit_service import (
    ACTION_LOGIN_FAILED,
    ACTION_LOGIN_SUCCESS,
    ACTION_LOGOUT,
    init_audit_table,
    list_audit_logs,
)
from services.auth_db import init_users_table
from services.database import init_db
from services.login_service import authenticate_with_role
from services.project_service import create_new_project_state, persist_project_state
from services.project_workflow_service import get_project_workflow, init_engineer_owned_project
from services.session_service import (
    clear_remembered_username,
    load_remembered_username,
    save_remembered_username,
)


class TestRoleLoginSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db = self._tmp.name
        init_db(self.db)
        init_users_table(self.db)
        init_audit_table(self.db)

    def tearDown(self) -> None:
        if os.path.exists(self.db):
            os.unlink(self.db)

    def test_successful_role_login(self) -> None:
        user, err = authenticate_with_role("akash", "Akash@123", ROLE_LABELS[ROLE_ENGINEER], self.db)
        self.assertIsNotNone(user)
        self.assertEqual(err, "")
        self.assertEqual(user.role, ROLE_ENGINEER)

    def test_role_mismatch_fails(self) -> None:
        user, err = authenticate_with_role("akash", "Akash@123", "Super Admin", self.db)
        self.assertIsNone(user)
        self.assertEqual(err, "Invalid username, password, or role.")

    def test_invalid_password_fails(self) -> None:
        user, err = authenticate_with_role("akash", "wrong", ROLE_LABELS[ROLE_ENGINEER], self.db)
        self.assertIsNone(user)
        self.assertIn("Invalid", err)

    def test_employee_id_login(self) -> None:
        user, err = authenticate_with_role("EMP-101", "Akash@123", ROLE_LABELS[ROLE_ENGINEER], self.db)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "akash")

    def test_login_audit_success_and_failure(self) -> None:
        authenticate_with_role("akash", "Akash@123", ROLE_LABELS[ROLE_ENGINEER], self.db)
        authenticate_with_role("akash", "wrong", ROLE_LABELS[ROLE_ENGINEER], self.db)
        logs = list_audit_logs(limit=10, db_path=self.db)
        actions = {e["action"] for e in logs}
        self.assertIn(ACTION_LOGIN_SUCCESS, actions)
        self.assertIn(ACTION_LOGIN_FAILED, actions)


class TestRememberMe(unittest.TestCase):
    def setUp(self) -> None:
        clear_remembered_username()

    def tearDown(self) -> None:
        clear_remembered_username()

    def test_remember_username_only(self) -> None:
        save_remembered_username("akash")
        self.assertEqual(load_remembered_username(), "akash")
        clear_remembered_username()
        self.assertEqual(load_remembered_username(), "")


class TestEngineerProjectOwnership(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db = self._tmp.name
        init_db(self.db)
        init_users_table(self.db)
        from services.auth_db import authenticate

        self.engineer = authenticate("akash", "Akash@123", self.db)
        assert self.engineer is not None

    def tearDown(self) -> None:
        if os.path.exists(self.db):
            os.unlink(self.db)

    def test_engineer_owned_project_metadata(self) -> None:
        state = create_new_project_state(self.engineer, self.db)
        persist_project_state(state, self.engineer, self.db)
        init_engineer_owned_project(state.project.project_id, self.engineer, self.db)
        wf = get_project_workflow(state.project.project_id, self.db)
        self.assertEqual(wf.assigned_to_username, "akash")
        self.assertEqual(wf.team_leader_id, self.engineer.team_leader_id)
        self.assertGreater(wf.assigned_duration_minutes, 0)


class TestLoginScreenUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        cls.root.destroy()

    def test_login_screen_has_role_dropdown(self) -> None:
        from ui.login_screen import LoginScreen

        screen = LoginScreen(self.root, on_login_success=lambda _u: None)
        screen.grid()
        screen.update_idletasks()
        self.assertEqual(screen.role_var.get(), "Select Role")
        self.assertIn("Select Role", screen.role_menu.cget("values"))
        screen.destroy()

    def test_empty_role_shows_error(self) -> None:
        from ui.login_screen import LoginScreen

        screen = LoginScreen(self.root, on_login_success=lambda _u: None)
        screen.grid()
        screen.username_entry.insert(0, "akash")
        screen.password_entry.insert(0, "Akash@123")
        screen._attempt_login()
        self.assertIn("Please select your role", screen.error_label.cget("text"))
        screen.destroy()

    def test_invalid_login_does_not_destroy_root(self) -> None:
        from ui.login_screen import LoginScreen

        screen = LoginScreen(self.root, on_login_success=lambda _u: None)
        screen.grid()
        screen.username_entry.insert(0, "akash")
        screen.password_entry.insert(0, "wrong")
        screen.role_var.set(ROLE_LABELS[ROLE_ENGINEER])
        screen._attempt_login()
        self.assertTrue(self.root.winfo_exists())
        screen.destroy()


class TestLogoutAudit(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._tmp.close()
        self.db = self._tmp.name
        init_audit_table(self.db)

    def tearDown(self) -> None:
        if os.path.exists(self.db):
            os.unlink(self.db)

    def test_logout_action_logged(self) -> None:
        from services.audit_service import log_audit

        log_audit(ACTION_LOGOUT, username="akash", user_id=1, db_path=self.db)
        logs = list_audit_logs(db_path=self.db)
        self.assertEqual(logs[0]["action"], ACTION_LOGOUT)


if __name__ == "__main__":
    unittest.main()
