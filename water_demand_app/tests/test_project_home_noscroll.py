"""Regression tests for no-scroll Project Home layout."""

from __future__ import annotations

import inspect
import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)


class TestProjectHomeNoScroll(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            from ui.dashboard import MainDashboard
            from ui.project_hub import ProjectHub

            cls.ctk = ctk
            cls.root = ctk.CTk()
            cls.root.withdraw()
            cls.MainDashboard = MainDashboard
            cls.ProjectHub = ProjectHub
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    @classmethod
    def tearDownClass(cls) -> None:
        if hasattr(cls, "root"):
            cls.root.destroy()

    def test_dashboard_uses_grid_not_scrollable_page(self) -> None:
        source = inspect.getsource(self.MainDashboard._build)
        self.assertNotIn("CTkScrollableFrame", source)
        self.assertIn("grid_rowconfigure(3, weight=1)", source)

    def test_project_hub_table_expands_with_weight(self) -> None:
        source = inspect.getsource(self.ProjectHub._build)
        self.assertIn("grid_rowconfigure(2, weight=1)", source)
        self.assertIn("CTkScrollableFrame", source)

    def test_delete_confirmation_includes_project_details(self) -> None:
        source = inspect.getsource(self.ProjectHub._delete_project)
        self.assertIn("Client:", source)
        self.assertIn("Delete Project Permanently", source)
        self.assertIn("This action cannot be undone.", source)
        self.assertIn("Unable to delete the project. Please try again.", source)

    def test_layout_fits_fixed_dashboard_structure(self) -> None:
        page = self.MainDashboard(self.root, on_new_project=lambda: None, on_open_project=lambda _id: None, on_exit=lambda: None)
        page.update_idletasks()
        self.assertIsNotNone(page.project_hub)
        self.assertEqual(len(page._stat_labels), 6)


if __name__ == "__main__":
    unittest.main()
