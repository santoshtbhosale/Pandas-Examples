"""Regression tests for single-window architecture and RWH removal."""

import os
import sys
import unittest

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_ROOT = os.path.join(WORKSPACE_ROOT, "water_demand_app")
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from config.page_visibility import visible_pages
from config.nbc_2026 import PROJECT_TYPE_RESIDENTIAL


class TestSingleWindowArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk
            from app_launcher import Application
            from _app_sidebar import ProjectWorkspace

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.app = Application()
            cls.app.withdraw()
            cls.app.update_idletasks()
            cls.workspace = ProjectWorkspace(cls.root)
            cls.workspace.withdraw()
            cls.workspace.update_idletasks()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "workspace"):
            cls.workspace.destroy()
        if hasattr(cls, "app"):
            cls.app.destroy()
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_application_has_single_root(self) -> None:
        self.assertIsInstance(self.app, self.ctk.CTk)

    def test_workspace_is_frame_not_toplevel(self) -> None:
        self.assertIsInstance(self.workspace, self.ctk.CTkFrame)

    def test_rwh_not_in_nav(self) -> None:
        keys = [k for k, _ in self.workspace.NAV]
        self.assertNotIn("RWH", keys)

    def test_rwh_not_in_page_visibility(self) -> None:
        pages = visible_pages(PROJECT_TYPE_RESIDENTIAL)
        self.assertNotIn("RWH", pages)

    def test_apply_state_rebuilds_project_page(self) -> None:
        self.workspace.ensure_pages_built()
        self.workspace.show("Project")
        from services.project_service import create_new_project_state

        self.workspace.apply_state(create_new_project_state())
        self.assertIn("Project", self.workspace.pages)
        self.assertEqual(self.workspace._current_page, "Project")
        self.assertNotIn("Residential", self.workspace.pages)

    def test_lazy_page_build(self) -> None:
        from _app_sidebar import ProjectWorkspace

        ws = ProjectWorkspace(self.root)
        ws.withdraw()
        self.assertFalse(ws._pages_built)
        ws.ensure_pages_built()
        self.assertTrue(ws._pages_built)
        self.assertIn("Project", ws.pages)
        ws.destroy()


if __name__ == "__main__":
    unittest.main()
