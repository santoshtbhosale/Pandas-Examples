"""Point 1 — Project Details GUI field removal tests."""

from __future__ import annotations

import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

REMOVED_FIELDS = (
    "project_location",
    "client_address",
    "client_contact",
    "client_email",
    "client_gst",
    "city",
    "state",
    "rainfall_zone",
    "climate",
)


class TestProjectDetailsCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            import customtkinter as ctk

            from ui.app_state import AppState
            from ui.pages.project_page import ProjectPage

            cls.ctk = ctk
            root = ctk.CTk()
            root.withdraw()
            state = AppState()
            state.project.project_type = "residential"
            cls.page = ProjectPage(root, state, on_next=lambda: None)
            cls.page.update_idletasks()
            root.destroy()
        except Exception as exc:
            raise unittest.SkipTest(f"GUI not available: {exc}") from exc

    def test_removed_fields_not_in_entries(self) -> None:
        for field in REMOVED_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn(field, self.page.entries)

    def test_core_fields_remain(self) -> None:
        for field in ("project_name", "client_name"):
            self.assertIn(field, self.page.entries)

    def test_no_plot_mode_widget(self) -> None:
        self.assertFalse(hasattr(self.page, "plot_mode_var"))

    def test_no_removed_metadata_fields_in_ui(self) -> None:
        self.assertFalse(hasattr(self.page, "project_type_display"))
        self.assertFalse(hasattr(self.page, "date_label"))
        self.assertTrue(hasattr(self.page, "project_no_label"))


if __name__ == "__main__":
    unittest.main()
