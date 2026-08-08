"""Point 1 — Project Details GUI field removal tests."""

from __future__ import annotations

import os
import sys
import unittest

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.dirname(APP_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

REMOVED_FIELDS = (
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
            import importlib.util

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

    def test_client_address_not_displayed(self) -> None:
        self.assertNotIn("client_address", self.page.entries)

    def test_contact_not_displayed(self) -> None:
        self.assertNotIn("client_contact", self.page.entries)

    def test_email_not_displayed(self) -> None:
        self.assertNotIn("client_email", self.page.entries)

    def test_gst_not_displayed(self) -> None:
        self.assertNotIn("client_gst", self.page.entries)

    def test_city_not_displayed(self) -> None:
        self.assertNotIn("city", self.page.entries)

    def test_state_not_displayed(self) -> None:
        self.assertNotIn("state", self.page.entries)

    def test_rainfall_zone_not_displayed(self) -> None:
        self.assertNotIn("rainfall_zone", self.page.entries)

    def test_climate_not_displayed(self) -> None:
        self.assertNotIn("climate", self.page.entries)

    def test_removed_fields_not_in_entries(self) -> None:
        for field in REMOVED_FIELDS:
            with self.subTest(field=field):
                self.assertNotIn(field, self.page.entries)

    def test_core_fields_remain(self) -> None:
        for field in ("project_name", "client_name", "project_location"):
            self.assertIn(field, self.page.entries)


if __name__ == "__main__":
    unittest.main()
